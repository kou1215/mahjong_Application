import random
from collections import Counter
from functools import lru_cache
import importlib

# Try to detect external `mahjong` library; if available we'll prefer it for shanten
try:
	_mahjong_lib = importlib.import_module('mahjong')
	_MAHJONG_AVAILABLE = True
except Exception:
	_mahjong_lib = None
	_MAHJONG_AVAILABLE = False

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


	
def format_hand_compact(hand):
	# return like "123m 456p 77E" style compact grouping
	suits = {'m': [], 'p': [], 's': []}
	honors = []
	for t in sort_hand(hand):
		if len(t) == 2 and t[1] in suits:
			suits[t[1]].append(t[0])
		else:
			honors.append(t)
	parts = []
	for s in ['m', 'p', 's']:
		if suits[s]:
			parts.append(''.join(suits[s]) + s)
	if honors:
		parts.append(' '.join(honors))
	return ' '.join(parts)


# --- Shanten calculation ---
def _build_index_map():
	order = {}
	idx = 0
	for s in ['m', 'p', 's']:
		for n in range(1, 10):
			order[f"{n}{s}"] = idx
			idx += 1
	for h in ['E', 'S', 'W', 'N', 'P', 'F', 'C']:
		order[h] = idx
		idx += 1
	return order


TILE_INDEX = _build_index_map()
INDEX_TILE = {v: k for k, v in TILE_INDEX.items()}


def hand_to_counts(hand):
	counts = [0] * 34
	for t in hand:
		i = TILE_INDEX.get(t)
		if i is not None:
			counts[i] += 1
	return counts


@lru_cache(maxsize=2048)
def _suit_best(counts_tuple):
	# counts_tuple is length-9 tuple for a suit (1..9)
	counts = list(counts_tuple)
	best_m = 0
	best_t = 0

	def dfs(pos, m, t):
		nonlocal best_m, best_t
		while pos < 9 and counts[pos] == 0:
			pos += 1
		if pos >= 9:
			if m + t > best_m + best_t:
				best_m, best_t = m, t
			return
		# try triplet
		if counts[pos] >= 3:
			counts[pos] -= 3
			dfs(pos, m + 1, t)
			counts[pos] += 3
		# try sequence
		if pos <= 6 and counts[pos] and counts[pos + 1] and counts[pos + 2]:
			counts[pos] -= 1
			counts[pos + 1] -= 1
			counts[pos + 2] -= 1
			dfs(pos, m + 1, t)
			counts[pos] += 1
			counts[pos + 1] += 1
			counts[pos + 2] += 1
		# try taatsu patterns (pair or two-consecutive)
		# pair-like (for taatsu)
		if counts[pos] >= 2:
			counts[pos] -= 2
			dfs(pos, m, t + 1)
			counts[pos] += 2
		# ryanmen/tanki-like
		if pos <= 7 and counts[pos] and counts[pos + 1]:
			counts[pos] -= 1
			counts[pos + 1] -= 1
			dfs(pos, m, t + 1)
			counts[pos] += 1
			counts[pos + 1] += 1
		# skip this tile (treat as isolated)
		# mark as visited and move on
		c = counts[pos]
		counts[pos] = 0
		dfs(pos + 1, m, t)
		counts[pos] = c

	dfs(0, 0, 0)
	return best_m, best_t


def shanten_standard(counts):
	# counts: length 34
	min_shanten = 8
	# try choosing pair (including no pair)
	for i in range(34):
		if counts[i] >= 2:
			c = list(counts)
			c[i] -= 2
			m = 0
			t = 0
			# honors
			for j in range(27, 34):
				if c[j] >= 3:
					m += c[j] // 3
			# suits
			for s in range(3):
				off = s * 9
				suit_counts = tuple(c[off:off + 9])
				sm, st = _suit_best(suit_counts)
				m += sm
				t += st
			sh = 8 - m * 2 - t - 1
			if sh < min_shanten:
				min_shanten = sh
	# also consider no pair
	c = list(counts)
	m = 0
	t = 0
	for j in range(27, 34):
		if c[j] >= 3:
			m += c[j] // 3
	for s in range(3):
		off = s * 9
		suit_counts = tuple(c[off:off + 9])
		sm, st = _suit_best(suit_counts)
		m += sm
		t += st
	sh = 8 - m * 2 - t
	if sh < min_shanten:
		min_shanten = sh
	return min_shanten


def shanten_chiitoitsu(counts):
	pairs = sum(1 for c in counts if c >= 2)
	blocks = sum(1 for c in counts if c > 0)
	sh = 6 - pairs + max(0, 7 - blocks)
	return sh


def shanten_kokushi(counts):
	terminals = [0, 8, 9, 17, 18, 26]  # 1&9 of each suit indices
	honors_idx = list(range(27, 34))
	uniques = 0
	pair = False
	for i in terminals + honors_idx:
		if counts[i] > 0:
			uniques += 1
		if counts[i] >= 2:
			pair = True
	sh = 13 - uniques - (1 if pair else 0)
	return sh


def shanten(hand):
	# If an external mahjong library is installed, try to use it.
	if _MAHJONG_AVAILABLE:
		try:
			# Common API: mahjong.shanten.Shanten
			try:
				from mahjong.shanten import Shanten
				sh = Shanten()
				# many implementations accept a list of tiles like ['1m','2m',...]
				return sh.calculate_shanten(hand)
			except Exception:
				# fallback: try module-level helpers
				try:
					from mahjong import shanten as sh_mod
					if hasattr(sh_mod, 'calculate_shanten'):
						return sh_mod.calculate_shanten(hand)
					if hasattr(sh_mod, 'shanten'):
						return sh_mod.shanten(hand)
				except Exception:
					pass
		except Exception:
			pass
	# Fallback to built-in implementation
	counts = hand_to_counts(hand)
	s_std = shanten_standard(counts)
	s_chi = shanten_chiitoitsu(counts)
	s_kok = shanten_kokushi(counts)
	return min(s_std, s_chi, s_kok)


def print_hands(hands):
	for i, h in enumerate(hands):
		s = format_hand_compact(h)
		sh = shanten(h)
		print(f"Player {i}: {len(h)} tiles -> {s}  (shanten: {sh})")


def simulate_simple_game(turns=8):
	out = run_simulation(turns)
	print(out)


def run_simulation(turns=8):
	wall = build_wall()
	hands = deal(wall)
	lines = []
	lines.append("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	lines.append("--- Initial hands ---")
	for i, h in enumerate(hands):
		s = format_hand_compact(h)
		sh = shanten(h)
		lines.append(f"Player {i}: {len(h)} tiles -> {s}  (shanten: {sh})")
	lines.append(f"Wall: {len(wall)} tiles remaining")

	for turn in range(turns):
		lines.append(f"\n--- Turn {turn + 1} ---")
		for p in range(4):
			if not wall:
				lines.append("Wall is empty.")
				return '\n'.join(lines)
			draw = wall.pop()
			hands[p].append(draw)
			# simple random discard
			discard_index = random.randrange(len(hands[p]))
			discard = hands[p].pop(discard_index)
			s = format_hand_compact(hands[p])
			sh = shanten(hands[p])
			lines.append(f"Player {p} draws {draw} and discards {discard} ({len(hands[p])} tiles) -> {s}  (shanten: {sh})")
		lines.append(f"Wall: {len(wall)} tiles remaining")

	lines.append("\n--- Final hands ---")
	for i, h in enumerate(hands):
		s = format_hand_compact(h)
		sh = shanten(h)
		lines.append(f"Player {i}: {len(h)} tiles -> {s}  (shanten: {sh})")

	return '\n'.join(lines)


def main():
	print("Simple Mahjong CLI — dealing and basic draw/discard simulation")
	simulate_simple_game(turns=8)


if __name__ == '__main__':
	main()

