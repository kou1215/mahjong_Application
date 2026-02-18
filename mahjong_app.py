import random
from collections import Counter

#このコードめっちゃいいね！！シンプルな麻雀の壁の構築、配牌、手牌のソート、そして基本的なドローと捨てのシミュレーションが実装されているね。これをベースにして、さらに複雑なルールや役の判定なども追加できそうだね。
def build_wall():
	suits = ['m', 'p', 's']
	tiles = []
	for s in suits:
		for n in range(1, 10):
			tiles.append(f"{n}{s}")
	honors = ['E', 'S', 'W', 'N', 'P', 'F', 'C']
	tiles += honors
	# 34 unique tiles, 4 copies each -> 136
	wall = []
	for t in tiles:
		wall.extend([t] * 4)
	random.shuffle(wall)
	return wall


def deal(wall):
	hands = [[] for _ in range(4)]
	# give 13 tiles to each
	for _ in range(13):
		for p in range(4):
			hands[p].append(wall.pop())
	# dealer (player 0) draws one extra to start (14)
	hands[0].append(wall.pop())
	return hands


def sort_hand(hand):
	order = {}
	idx = 0
	for s in ['m', 'p', 's']:
		for n in range(1, 10):
			order[f"{n}{s}"] = idx
			idx += 1
	for h in ['E', 'S', 'W', 'N', 'P', 'F', 'C']:
		order[h] = idx
		idx += 1
	return sorted(hand, key=lambda t: order.get(t, 999))


def print_hands(hands):
	for i, h in enumerate(hands):
		s = sort_hand(h)
		print(f"Player {i}: {len(h)} tiles -> {' '.join(s)}")


def simulate_simple_game(turns=8):
	wall = build_wall()
	hands = deal(wall)

	print("--- Initial hands ---")
	print_hands(hands)
	print(f"Wall: {len(wall)} tiles remaining")

	for turn in range(turns):
		print(f"\n--- Turn {turn + 1} ---")
		for p in range(4):
			if not wall:
				print("Wall is empty.")
				return
			draw = wall.pop()
			hands[p].append(draw)
			# simple random discard
			discard_index = random.randrange(len(hands[p]))
			discard = hands[p].pop(discard_index)
			print(f"Player {p} draws {draw} and discards {discard} ({len(hands[p])} tiles)")
		print(f"Wall: {len(wall)} tiles remaining")

	print("\n--- Final hands ---")
	print_hands(hands)


def main():
	print("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	simulate_simple_game(turns=8)


if __name__ == '__main__':
	main()

