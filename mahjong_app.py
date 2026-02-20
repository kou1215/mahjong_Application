"""
後方互換性のためのラッパーモジュール
新しいコードは models/ や logic/ を直接使用してください

このモジュールは既存コードとの互換性を保つために以下の関数を提供しています：
- build_wall()
- deal()
- sort_hand()
- format_hand_compact()
- shanten()
- run_simulation()
"""

from models.tile_utils import (
	build_wall,
	sort_hand,
	format_hand_compact,
	hand_to_counts,
)
from logic.shanten import calculate_shanten as shanten
from models.game import Game


def deal(wall):
	"""
	古い API との互換性のため
	壁から4人分の手牌を配牌する
	"""
	hands = [[] for _ in range(4)]
	# give 13 tiles to each
	for _ in range(13):
		for p in range(4):
			hands[p].append(wall.pop())
	# dealer (player 0) draws one extra to start (14)
	hands[0].append(wall.pop())
	return hands


def print_hands(hands):
	"""古い API との互換性のため"""
	for i, h in enumerate(hands):
		s = format_hand_compact(h)
		sh = shanten(h)
		print(f"Player {i}: {len(h)} tiles -> {s}  (shanten: {sh})")


def simulate_simple_game(turns=8):
	"""古い API との互換性のため"""
	out = run_simulation(turns)
	print(out)


def run_simulation(turns=8):
	"""
	古い API との互換性のため
	シンプルなシミュレーションを実行
	"""
	game = Game(num_players=4, human_player_id=0)
	game.start_game()

	lines = []
	lines.append("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	lines.append("--- Initial hands ---")
	for player in game.players:
		s = format_hand_compact(player.hand.to_list())
		sh = shanten(player.hand.to_list())
		lines.append(f"Player {player.player_id}: {len(player.hand)} tiles -> {s}  (shanten: {sh})")
	lines.append(f"Wall: {len(game.wall)} tiles remaining")

	for turn in range(turns):
		if game.is_game_over:
			break
		lines.append(f"\n--- Turn {turn + 1} ---")

		for p in range(game.num_players):
			if game.is_game_over:
				break
			player = game.players[p]
			if player.is_ai:
				discard_idx = player.choose_discard()
				game.process_discard(discard_idx)
				s = format_hand_compact(player.hand.to_list())
				sh = shanten(player.hand.to_list())
				lines.append(f"Player {p} discards ({len(player.hand)} tiles) -> {s}  (shanten: {sh})")

		lines.append(f"Wall: {len(game.wall)} tiles remaining")

	lines.append("\n--- Final hands ---")
	for player in game.players:
		s = format_hand_compact(player.hand.to_list())
		sh = shanten(player.hand.to_list())
		lines.append(f"Player {player.player_id}: {len(player.hand)} tiles -> {s}  (shanten: {sh})")

	return '\n'.join(lines)


def main():
	"""メイン関数"""
	print("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	simulate_simple_game(turns=8)


if __name__ == '__main__':
	main()


