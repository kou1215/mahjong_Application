"""
プレイヤーのモデル
"""
import random
from typing import List

from models.hand import Hand
from logic.shanten import calculate_shanten


class Player:
	"""プレイヤーの基本クラス"""

	def __init__(self, player_id: int, is_ai: bool = False):
		"""
		Args:
			player_id: プレイヤーID (0-3)
			is_ai: AIプレイヤーか
		"""
		self.player_id = player_id
		self.is_ai = is_ai
		self.hand = Hand()
		self.discards: List[str] = []

	def add_tile(self, tile: str) -> None:
		"""ツモ牌を追加"""
		self.hand.add_tile(tile)

	def get_shanten(self) -> int:
		"""シャンテン数を取得"""
		return self.hand.get_shanten()

	def choose_discard(self) -> int:
		"""
		捨て牌のインデックスを選択
		ゲーム側で呼び出される
		
		Returns:
			捨てる牌のインデックス
		"""
		if self.is_ai:
			raise NotImplementedError("AIPlayerを使用してください")
		# 人間プレイヤーの場合、Webから指定される
		return 0  # デフォルト値（実際はWebから受け取る）

	def discard_tile(self, index: int) -> str:
		"""指定インデックスの牌を捨てる"""
		tile = self.hand.remove_tile(index)
		self.discards.append(tile)
		return tile

	def to_dict(self) -> dict:
		"""プレイヤー情報を辞書化"""
		return {
			'player_id': self.player_id,
			'hand': self.hand.to_list(),
			'shanten': self.get_shanten(),
			'discards': self.discards,
			'is_ai': self.is_ai,
		}

	def __repr__(self) -> str:
		return f"Player({self.player_id}, is_ai={self.is_ai})"


class AIPlayer(Player):
	"""AI制御のプレイヤー"""

	def __init__(self, player_id: int):
		super().__init__(player_id, is_ai=True)

	def choose_discard(self) -> int:
		"""
		最もシャンテン数が低くなる捨て牌を選択
		複数候補がある場合はランダムに選ぶ
		
		Returns:
			捨てる牌のインデックス
		"""
		if len(self.hand) == 0:
			return 0

		# 各牌を捨てた場合のシャンテン数を計算
		min_shanten = None
		best_discards = []

		for i in range(len(self.hand)):
			# 一時的に牌を削除してシャンテン数を計算
			temp_tiles = self.hand.to_list()
			removed = temp_tiles.pop(i)
			s = calculate_shanten(temp_tiles)

			if min_shanten is None or s < min_shanten:
				min_shanten = s
				best_discards = [i]
			elif s == min_shanten:
				best_discards.append(i)

		# 複数候補がある場合はランダムに選択
		return random.choice(best_discards)
