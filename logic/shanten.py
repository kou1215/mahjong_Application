"""
シャンテン数計算
"""
from functools import lru_cache
from typing import List
import importlib

from models.tile_utils import hand_to_counts


# Try to detect external `mahjong` library; if available we'll prefer it for shanten
try:
	_mahjong_lib = importlib.import_module('mahjong')
	_MAHJONG_AVAILABLE = True
except Exception:
	_mahjong_lib = None
	_MAHJONG_AVAILABLE = False


@lru_cache(maxsize=2048)
def _suit_best(counts_tuple):
	"""
	スーツ内での最良メルド数を計算（メモ化版）
	counts_tuple is length-9 tuple for a suit (1..9)
	"""
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
		c = counts[pos]
		counts[pos] = 0
		dfs(pos + 1, m, t)
		counts[pos] = c

	dfs(0, 0, 0)
	return best_m, best_t


def shanten_standard(counts: List[int]) -> int:
	"""標準形でのシャンテン数を計算"""
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
	# シャンテン数は 0 未満にはしない
	return max(min_shanten, 0)


def shanten_chiitoitsu(counts: List[int]) -> int:
	"""七対子のシャンテン数を計算"""
	pairs = sum(1 for c in counts if c >= 2)
	blocks = sum(1 for c in counts if c > 0)
	sh = 6 - pairs + max(0, 7 - blocks)
	return sh


def shanten_kokushi(counts: List[int]) -> int:
	"""国士無双のシャンテン数を計算"""
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


def calculate_shanten(hand: List[str]) -> int:
	"""
	手牌のシャンテン数を計算
	mahjong.agari.Agariを使用した正確な計算
	"""
	from mahjong.agari import Agari
	
	agari = Agari()
	counts = hand_to_counts(hand)
	valid_count = sum(counts)
	# if hand doesn't contain exactly 14 valid tiles, treat as invalid/high shanten
	if valid_count != 14:
		return 8
	
	# アガリ形なら -1
	if agari.is_agari(counts):
		return -1
	
	# シャンテン値：単体の削除でテンパイになるかをチェック
	for i in range(34):
		if counts[i] > 0:
			counts[i] -= 1
			if agari.is_agari(counts):
				counts[i] += 1
				return 0  # テンパイ
			counts[i] += 1
	
	# それ以外は以前のフォールバック実装に委ねる
	# counts は既に定義
	s_std = shanten_standard(counts)
	s_chi = shanten_chiitoitsu(counts)
	s_kok = shanten_kokushi(counts)
	return min(s_std, s_chi, s_kok)
