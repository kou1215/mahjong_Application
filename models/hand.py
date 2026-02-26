"""
手牌を表すクラス
"""
from typing import List, Dict, Optional, Any

from models.tile_utils import sort_hand, format_hand_compact
from logic.shanten import calculate_shanten
from logic.agari import AgariChecker
from mahjong.constants import EAST


class Hand:
	"""手牌を管理するクラス"""

	def __init__(self, tiles: List[str] = None):
		"""
		Args:
			tiles: 手牌リスト（初期値: 空）
		"""
		self.tiles = tiles if tiles is not None else []
		self._agari_checker = AgariChecker()

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

	def get_shanten(self, open_melds_count: int = 0) -> int:
		"""シャンテン数を取得"""
		return calculate_shanten(self.tiles, open_melds_count=open_melds_count)

	def get_compact_format(self) -> str:
		"""コンパクト形式で取得"""
		return format_hand_compact(self.tiles)

	def is_winning(self) -> bool:
		"""
		手牌がアガり形かどうかを判定
		
		Returns:
			アガり形なら True、そうでなければ False
		"""
		if len(self.tiles) != 14:
			return False
		return self._agari_checker.is_agari(self.tiles)

	def estimate_win_value(
		self,
		win_tile: str,
		is_tsumo: bool = True,
		is_dealer: bool = False,
		melds: list = None,
		player_wind: int = EAST,
		round_wind: int = EAST,
		dora_indicators: list = None,
	) -> Dict[str, Any]:
		"""
		アガった場合の手数を計算
		
		Args:
			win_tile: アガり牌
			is_tsumo: ツモ和了かどうか
			is_dealer: 親かどうか
			player_wind: 自風（1:東, 2:南, 3:西, 4:北）
			round_wind: 場風（1:東, 2:南, 3:西, 4:北）
			dora_indicators: ドラ表示牌のリスト
		
		Returns:
			{
				'valid': bool,
				'error': Optional[str],
				'han': int,
				'fu': int,
				'cost': dict,
				'limit': str,
				'yaku': List[str],
			}
		"""
		return self._agari_checker.estimate_hand_value(
			self.tiles, win_tile, is_tsumo, is_dealer,
			melds=melds,
			player_wind=player_wind, round_wind=round_wind,
			dora_indicators=dora_indicators
		)

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
