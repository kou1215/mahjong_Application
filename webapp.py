
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
		return None
	
	game = Game(num_players=4, human_player_id=0)
	game.current_turn = game_data.get('current_turn', 0)
	game.is_game_over = game_data.get('is_game_over', False)
	game.wall = game_data.get('wall', [])
	game.dora_indicator = game_data.get('dora_indicator')
	game.dead_wall = game_data.get('dead_wall', [])
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

	return game


def save_game_to_session(game: Game) -> None:
	"""ゲーム状態をセッションに保存"""
	session['game_data'] = game.to_json_serializable()


def build_state_response(game: Game, result: dict | None = None) -> dict:
	"""現在のゲーム状態をフロント向けJSONに整形"""
	result = result or {}
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
		remaining_draws=max(0, len(game.wall))
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
	except (TypeError, ValueError):
		return jsonify({'error': 'Invalid parameters'}), 400

	if player_id != game.current_turn:
		return jsonify({'error': f'現在の手番は Player {game.current_turn} です'}), 400

	try:
		result = game.process_discard(discard_index)
	except ValueError as e:
		return jsonify({'error': str(e)}), 400
	if result.get('error'):
		return jsonify({'error': result.get('error')}), 400

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
	except (TypeError, ValueError):
		return jsonify({'error': 'Invalid parameters'}), 400

	if not win_tile:
		return jsonify({'error': 'win_tile is required'}), 400

	# アガり判定
	is_agari = game.check_agari(player_id)
	
	# 点数計算
	value_result = None
	if is_agari:
		value_result = game.estimate_agari_value(player_id, win_tile, is_tsumo)

	response_data = {
		'agari': is_agari,
		'player_id': player_id,
		'win_tile': win_tile,
		'is_tsumo': is_tsumo,
		'value': value_result if is_agari else None,
	}

	return jsonify(response_data)


if __name__ == '__main__':
	app.run(debug=True)
