"""
スタンドアロンのCLI版麻雀シミュレータ
"""
from models.game import Game
from models.tile_utils import format_hand_compact


def print_hands(game: Game) -> None:
	"""全プレイヤーの手牌を表示"""
	for player in game.players:
		s = format_hand_compact(player.hand.to_list())
		sh = player.get_shanten()
		print(f"Player {player.player_id}: {len(player.hand)} tiles -> {s}  (shanten: {sh})")


def simulate_game(turns: int = 8) -> None:
	"""シミュレーションを実行"""
	game = Game(num_players=4, human_player_id=0)
	game.start_game()

	print("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	print("--- Initial hands ---")
	print_hands(game)
	print(f"Wall: {len(game.wall)} tiles remaining\n")

	for turn in range(turns):
		if game.is_game_over:
			break
		print(f"--- Turn {turn + 1} ---")

		# プレイヤー0（人間）が捨てカードを選択
		player0 = game.players[0]
		if player0.is_ai:
			discard_idx = player0.choose_discard()
		else:
			# 適当に最初のカードを捨てるという想定
			discard_idx = 0

		# ターン処理（AI プレイヤーの自動処理も含む）
		result = game.process_discard(discard_idx)
		
		print(f"Player 0 discards {result['discarded_tile']} ({len(player0.hand)} tiles)")
		print(f"  shanten: {player0.get_shanten()}")
		if result.get('player0_draw'):
			print(f"  (drew: {result['player0_draw']})")
		
		# AI ログを表示
		for log in result['auto_log']:
			player = game.players[log['player']]
			print(f"Player {log['player']} discards {log['discarded']} ({len(player.hand)} tiles)")
			print(f"  shanten: {log['shanten']}")
			if 'drawn' in log:
				print(f"  (drew: {log['drawn']})")

		print(f"Wall: {result['wall_count']} tiles remaining")

	print("\n--- Final hands ---")
	print_hands(game)


def main():
	"""メイン関数"""
	print("Mahjong Simulator - CLI Mode\n")
	simulate_game(turns=8)


if __name__ == '__main__':
	main()
