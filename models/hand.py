"""
手牌を表すクラス
"""
from typing import List

from models.tile_utils import sort_hand, format_hand_compact
from logic.shanten import calculate_shanten


class Hand:
	"""手牌を管理するクラス"""

	def __init__(self, tiles: List[str] = None):
		"""
		Args:
			tiles: 手牌リスト（初期値: 空）
		"""
		self.tiles = tiles if tiles is not None else []

	def add_tile(self, tile: str) -> None:
		"""牌を手に追加"""
		self.tiles.append(tile)
		self.sort()

	def remove_tile(self, index: int) -> str:
		"""指定インデックスの牌を削除して返す"""
		if index < 0 or index >= len(self.tiles):
			raise IndexError(f"Invalid tile index: {index}")
		return self.tiles.pop(index)

	def sort(self) -> None:
		"""手牌をソート"""
		self.tiles = sort_hand(self.tiles)

	def get_shanten(self) -> int:
		"""シャンテン数を取得"""
		return calculate_shanten(self.tiles)

	def get_compact_format(self) -> str:
		"""コンパクト形式で取得"""
		return format_hand_compact(self.tiles)

	def copy(self) -> 'Hand':
		"""手牌をコピー"""
		return Hand(self.tiles[:])

	def to_list(self) -> List[str]:
		"""牌リストとして取得"""
		return self.tiles[:]

	def __len__(self) -> int:
		"""手牌枚数"""
		return len(self.tiles)

	def __str__(self) -> str:
		return self.get_compact_format()

	def __repr__(self) -> str:
		return f"Hand({len(self.tiles)} tiles: {self.get_compact_format()})"
