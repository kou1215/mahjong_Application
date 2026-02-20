
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from models.game import Game
from models.tile_utils import format_hand_compact

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
	
	# プレイヤーの手牌を復元
	players_data = game_data.get('players', [])
	for i, p_data in enumerate(players_data):
		game.players[i].hand.tiles = p_data.get('hand', [])
		game.players[i].discards = p_data.get('discards', [])
	
	return game


def save_game_to_session(game: Game) -> None:
	"""ゲーム状態をセッションに保存"""
	session['game_data'] = game.to_json_serializable()


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
		hands_view.append({
			'player': player.player_id,
			'tiles': player.hand.to_list(),
			'shanten': player.get_shanten(),
			'compact': format_hand_compact(player.hand.to_list()),
		})

	return render_template('index.html', turns=0, hands_view=hands_view)


# 新しいルート: /discard
@app.route('/discard', methods=['POST'])
def discard():
	# セッションからゲーム状態を取得
	game = get_game_from_session()
	if game is None:
		return jsonify({'error': 'No game in progress'}), 400

	# POSTデータからdiscard_indexを取得
	try:
		discard_index = int(request.form.get('discard_index'))
	except (TypeError, ValueError):
		return jsonify({'error': 'Invalid discard index'}), 400

	# ターン処理
	try:
		result = game.process_discard(discard_index)
	except ValueError as e:
		return jsonify({'error': str(e)}), 400

	# ゲーム状態をセッションに保存
	save_game_to_session(game)

	# レスポンスを作成
	response_data = {
		'discarded_tile': result['discarded_tile'],
		'drawn_tile': result.get('drawn_tile'),
		'player0_draw': result.get('player0_draw'),
		'auto_log': result['auto_log'],
		'wall_count': result['wall_count'],
		'is_game_over': result['is_game_over'],
		'hands': [p.hand.to_list() for p in game.players],
		'shanten_list': [p.get_shanten() for p in game.players],
	}

	return jsonify(response_data)


if __name__ == '__main__':
	app.run(debug=True)
