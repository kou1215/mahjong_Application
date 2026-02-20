"""
牌操作ユーティリティ
"""
import random
from typing import List


def build_wall() -> List[str]:
	"""
	標準的な麻雀の壁を生成する（136枚）
	"""
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


def get_tile_order() -> dict:
	"""牌の順序マッピングを返す"""
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


def get_tile_index() -> tuple:
	"""(TILE_INDEX, INDEX_TILE) を返す"""
	tile_index = get_tile_order()
	index_tile = {v: k for k, v in tile_index.items()}
	return tile_index, index_tile


TILE_INDEX, INDEX_TILE = get_tile_index()


def sort_hand(hand: List[str]) -> List[str]:
	"""手牌を標準順序でソート"""
	order = get_tile_order()
	return sorted(hand, key=lambda t: order.get(t, 999))


def format_hand_compact(hand: List[str]) -> str:
	"""
	手牌をコンパクト形式でフォーマット
	例: "123m 456p 77E"
	"""
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


def hand_to_counts(hand: List[str]) -> List[int]:
	"""手牌をカウント配列に変換（34要素）"""
	counts = [0] * 34
	for t in hand:
		i = TILE_INDEX.get(t)
		if i is not None:
			counts[i] += 1
	return counts
