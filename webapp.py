from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from models.game import Game
from models.tile_utils import format_hand_compact
from logic.calls import CallChecker
from mahjong.constants import EAST

app = Flask(__name__)
# セッション用のシークレットキー（本番ではより安全な値に）
app.secret_key = 'your_secret_key_here'


def get_game_from_session() -> Game:
	"""セッションからゲーム状態を復元"""
	game_data = session.get('game_data')
	if game_data is None:
		game = Game(num_players=4, human_player_id=0)
		game.start_game()
		# ★新規ゲーム開始時のみテンパイ配牌
		game.players[0].hand.tiles = ['1m','2m','3m','4m','5m','6m','7m','8m','9m','1p','1p','1p','2s','3s']
		save_game_to_session(game)
		return game
		
	
	game = Game(num_players=4, human_player_id=0)
	game.current_turn = game_data.get('current_turn', 0)
	game.is_game_over = game_data.get('is_game_over', False)
	game.wall = game_data.get('wall', [])
	game.dora_indicator = game_data.get('dora_indicator')
	game.dead_wall = game_data.get('dead_wall', [])
	game.ura_dora_indicator = game_data.get('ura_dora_indicator')
	game.round_wind = game_data.get('round_wind', EAST)
	game.phase = game_data.get('phase', 'discard')
	game.last_discarded = game_data.get('last_discarded')
	game.pending_calls = game_data.get('pending_calls', [])
	game.passed_callers = game_data.get('passed_callers', [])
	game.current_discarder_id = game_data.get('current_discarder_id')

	# プレイヤーの手牌を復元
	players_data = game_data.get('players', [])
	for i, p_data in enumerate(players_data):
		game.players[i].hand.tiles = p_data.get('hand', [])
		game.players[i].discards = p_data.get('discards', [])
		game.players[i].melds = p_data.get('melds', [])
		# is_riichiフラグも復元
		game.players[i].is_riichi = p_data.get('is_riichi', False)


	# received_callsも復元
	game.received_calls = game_data.get('received_calls', {})

	return game


def save_game_to_session(game: Game) -> None:
	"""ゲーム状態をセッションに保存"""
	session['game_data'] = game.to_json_serializable()


def build_state_response(game: Game, result: dict | None = None) -> dict:
	"""現在のゲーム状態をフロント向けJSONに整形"""
	result = result or {}
	# リーチ判定（条件分解＋デバッグ出力）
	player0 = game.players[0]
	is_my_turn = (game.current_turn == 0)
	is_discard_phase = (game.phase == 'discard')
	is_not_riichi = not getattr(player0, 'is_riichi', False)
	is_menzen = getattr(player0, 'is_menzen', len(player0.melds) == 0)
	is_tenpai = (player0.get_shanten() <= 0)

	can_riichi = is_my_turn and is_discard_phase and is_not_riichi and is_menzen and is_tenpai
	print(f"[DEBUG Riichi] turn:{is_my_turn}, phase:{is_discard_phase}, not_riichi:{is_not_riichi}, menzen:{is_menzen}, tenpai:{is_tenpai} -> can_riichi:{can_riichi}")
	response_data = {
		'current_turn': game.current_turn,
		'phase': game.phase,
		'awaiting_call': result.get('awaiting_call', game.phase == 'call_wait'),
		'discarded_tile': result.get('discarded_tile', game.last_discarded),
		'discarder_id': result.get('discarder_id', game.current_discarder_id),
		'available_calls': result.get('available_calls', game.pending_calls),
		'next_draw': result.get('next_draw'),
		'player0_draw': result.get('player0_draw'),
		'auto_log': result.get('auto_log', []),
		'wall_count': result.get('wall_count', len(game.wall)),
		'is_game_over': result.get('is_game_over', game.is_game_over),
		'hands': [p.hand.to_list() for p in game.players],
		'shanten_list': [p.get_shanten() for p in game.players],
		'dora_indicator': game.dora_indicator,
		'remaining_draws': result.get('remaining_draws', max(0, len(game.wall))),
		'melds': [p.melds for p in game.players],
		'agari_tiles': [game.get_agari_tiles(i) for i in range(game.num_players)],
		'can_riichi': can_riichi,
		'is_riichi': [p.is_riichi for p in game.players],
	}
	if 'ok' in result:
		response_data['ok'] = result['ok']
	if 'action' in result:
		response_data['action'] = result['action']
	if 'error' in result:
		response_data['error'] = result['error']
	if 'agari' in result:
		response_data['agari'] = result['agari']
	if 'type' in result:
		response_data['type'] = result['type']
	if 'player_id' in result:
		response_data['player_id'] = result['player_id']
	if 'win_tile' in result:
		response_data['win_tile'] = result['win_tile']
	if 'value' in result:
		response_data['value'] = result['value']
	return response_data


@app.route('/reset')
def reset():
	session.clear()
	return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
	hands_view = None

	# ゲーム状態を取得または新規作成
	game = get_game_from_session()
	if game is None:
		game = Game(num_players=4, human_player_id=0)
		game.start_game()
		save_game_to_session(game)

	# hands_viewの作成
	hands_view = []
	for player in game.players:
		shanten_val = player.get_shanten()
		print(f"[DEBUG] Player {player.player_id}: shanten={shanten_val}, hand={player.hand.to_list()}")
		hands_view.append({
			'player': player.player_id,
			'tiles': player.hand.to_list(),
			'shanten': shanten_val,
			'compact': format_hand_compact(player.hand.to_list()),
			'discards': player.discards,
			'melds': player.melds,
			'agari_tiles': game.get_agari_tiles(player.player_id),
		})

	agari_tiles_view = [game.get_agari_tiles(i) for i in range(game.num_players)]

	# can_riichi判定を追加
	player0 = game.players[0]
	can_riichi = (
		game.current_turn == 0 and
		game.phase == 'discard' and
		not getattr(player0, 'is_riichi', False) and
		getattr(player0, 'is_menzen', len(player0.melds) == 0) and
		player0.get_shanten() <= 0
	)

	return render_template(
		'index.html',
		turns=0,
		hands_view=hands_view,
		current_turn=game.current_turn,
		phase=game.phase,
		pending_calls=game.pending_calls,
		last_discarded=game.last_discarded,
		agari_tiles_view=agari_tiles_view,
		dora_indicator=game.dora_indicator,
		remaining_draws=max(0, len(game.wall)),
		can_riichi=can_riichi
	)


# 新しいルート: /discard
@app.route('/discard', methods=['POST'])
def discard():
	# セッションからゲーム状態を取得
	game = get_game_from_session()
	if game is None:
		return jsonify({'error': 'No game in progress'}), 400


	# Player 0 の捨て牌（他プレイヤーはAI自動）
	try:
		player_id = int(request.form.get('player_id', game.current_turn))
		discard_index = int(request.form.get('discard_index'))
		declare_riichi = request.form.get('declare_riichi', 'false').lower() == 'true'
	except (TypeError, ValueError):
		return jsonify({'error': 'Invalid parameters'}), 400

	if player_id != game.current_turn:
		return jsonify({'error': f'現在の手番は Player {game.current_turn} です'}), 400

	try:
		result = game.process_discard(discard_index, declare_riichi=declare_riichi)
	except ValueError as e:
		return jsonify({'error': str(e)}), 400
	if result.get('error'):
		return jsonify({'error': result.get('error')}), 400

	# デバッグ用: Player 0のリーチフラグ状態を出力
	print(f"--- DEBUG: Player 0 Riichi Status After Discard ---")
	print(f"Flag in Object: {game.players[0].is_riichi}")
	print(f"--------------------------------------------------")
	# ゲーム状態をセッションに保存
	save_game_to_session(game)
	return jsonify(build_state_response(game, result))


@app.route('/check_calls', methods=['POST'])
def check_calls():
	"""捨て牌に対する各プレイヤーの鳴き可否を返す（フロントがボタン表示に使用）"""
	game = get_game_from_session()
	if game is None:
		return jsonify({'error': 'No game in progress'}), 400

	discarded = request.json.get('discarded')
	if not discarded:
		return jsonify({'error': 'discarded is required'}), 400

	results = []
	for pid in range(len(game.players)):
		if pid == game.human_player_id:
			continue
		calls = game.check_available_calls(pid, discarded)
		calls['can_kan'] = CallChecker.can_kan(game.players[pid].hand.to_list(), discarded)
		results.append({'player_id': pid, 'calls': calls})

	return jsonify({'discarded': discarded, 'results': results})


@app.route('/apply_call', methods=['POST'])
def apply_call():
	"""フロントから鳴き実行（pong/chow/kan/ron/pass）を受け付ける"""
	game = get_game_from_session()
	if game is None:
		return jsonify({'error': 'No game in progress'}), 400

	try:
		player_id = int(request.json.get('player_id'))
		action = request.json.get('action')
		tiles = request.json.get('tiles', [])
	except Exception:
		return jsonify({'error': 'Invalid parameters'}), 400

	result = game.resolve_pending_call(player_id=player_id, action=action, tiles=tiles)
	if not result.get('ok', False):
		return jsonify({'error': result.get('error', 'Failed to apply call')}), 400

	save_game_to_session(game)
	return jsonify(build_state_response(game, result))


# 新しいルート: /check_agari
@app.route('/check_agari', methods=['POST'])
def check_agari():
	"""アガり判定と点数計算"""
	game = get_game_from_session()
	if game is None:
		return jsonify({'error': 'No game in progress'}), 400

	try:
		player_id = int(request.json.get('player_id', 0))
		win_tile = request.json.get('win_tile')
		is_tsumo = request.json.get('is_tsumo', True)
		is_riichi = request.json.get('is_riichi', False)
	except (TypeError, ValueError):
		return jsonify({'error': 'Invalid parameters'}), 400

	if not win_tile:
		return jsonify({'error': 'win_tile is required'}), 400

	# アガり判定＋点数計算＋裏ドラ
	win_result = game.check_and_calculate_win(player_id, win_tile, is_tsumo, is_riichi=is_riichi)
	win_result['is_tsumo'] = is_tsumo
	return jsonify(win_result)


if __name__ == '__main__':
	app.run(debug=True)
