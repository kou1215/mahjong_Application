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
		# 鳴きのリスト（各鳴きは dict: {type, tiles}）
		# type: 'pon', 'chow', 'minkan', 'ankan'
		self.melds: List[dict] = []
		self.is_riichi: bool = False  # リーチ状態

	@property
	def is_menzen(self) -> bool:
		"""門前（副露なし、暗槓のみ可）かどうか判定。"""
		# 暗槓以外の副露がなければ門前
		for meld in self.melds:
			# meld が辞書型で保存されている場合（理想的）
			if isinstance(meld, dict):
				if meld.get("type") != "ankan":
					return False
			# meld がリスト型に変換されてしまっている場合（セッション復元後など）
			# 暗槓は必ず同じ牌が4枚のリストになることを利用して判別する
			elif isinstance(meld, list):
				if len(meld) != 4 or not all(t == meld[0] for t in meld):
					return False
		return True

	def add_tile(self, tile: str) -> None:
		"""ツモ牌を追加"""
		self.hand.add_tile(tile)

	def get_shanten(self) -> int:
		"""シャンテン数を取得"""
		return self.hand.get_shanten(open_melds_count=len(self.melds))

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

	def call_pong(self, tiles: List[str]) -> bool:
		"""
		ポンを成立させる
		Args:
			tiles: ポンを作る3つの牌
		Returns:
			成功なら True
		"""
		if len(tiles) != 3 or not all(t == tiles[0] for t in tiles):
			return False
		# 手牌から牌を削除
		for tile in tiles[:2]:  # 捨てられた牌を除く2枚を削除
			if tile in self.hand.tiles:
				self.hand.remove_tile(self.hand.tiles.index(tile))
			else:
				return False
		# メルドに追加
		self.melds.append({"type": "pon", "tiles": tiles})
		self.hand.sort()
		return True

	def call_chow(self, tiles: List[str], discarded_tile: str = None) -> bool:
		"""
		チーを成立させる
		Args:
			tiles: チーを作る3つの牌（連続）
			discarded_tile: 他家の捨て牌（指定がない場合は従来互換動作）
		Returns:
			成功なら True
		"""
		if len(tiles) != 3:
			return False

		tiles_to_remove = []
		if discarded_tile is None:
			tiles_to_remove = tiles[1:]
		else:
			tiles_to_remove = list(tiles)
			if discarded_tile not in tiles_to_remove:
				return False
			tiles_to_remove.remove(discarded_tile)

		for tile in tiles_to_remove:
			if tile in self.hand.tiles:
				self.hand.remove_tile(self.hand.tiles.index(tile))
			else:
				return False

		self.melds.append({"type": "chow", "tiles": tiles})
		self.hand.sort()
		return True

	def call_kan(self, tile: str, is_closed: bool = False) -> bool:
		"""
		カンを成立させる（簡易実装）
		Args:
			tile: カンに使う牌の文字列（例: '5p'）
			is_closed: 暗槓かどうか（True=暗槓, False=明槓）
		Returns:
			成功なら True
		"""
		required = 4 if is_closed else 3
		if self.hand.to_list().count(tile) < required:
			return False
		for _ in range(required):
			if tile in self.hand.tiles:
				self.hand.remove_tile(self.hand.tiles.index(tile))
			else:
				return False
		meld_type = "ankan" if is_closed else "minkan"
		self.melds.append({"type": meld_type, "tiles": [tile]*4})
		self.hand.sort()
		return True

	def to_dict(self) -> dict:
		"""プレイヤー情報を辞書化"""
		return {
			'player_id': self.player_id,
			'hand': self.hand.to_list(),
			'shanten': self.get_shanten(),
			'discards': self.discards,
			'melds': self.melds,
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
