"""
ゲーム全体の管理
"""
from typing import List, Optional, Dict, Any

from models.tile_utils import build_wall
from models.player import Player, AIPlayer
from logic.agari import AgariChecker



class Game:
	"""麻雀ゲーム全体を管理するクラス"""

	def __init__(self, num_players: int = 4, human_player_id: int = 0):
		"""
		Args:
			num_players: プレイヤー数（デフォルト: 4）
			human_player_id: 人間プレイヤーのID
		"""
		self.num_players = num_players
		self.human_player_id = human_player_id
		self.players: List[Player] = []
		self.wall: List[str] = []
		self.current_turn = 0
		self.is_game_over = False
		self._agari_checker = AgariChecker()
		self._initialize_players()

	def _initialize_players(self) -> None:
		"""プレイヤーを初期化"""
		for i in range(self.num_players):
			if i == self.human_player_id:
				self.players.append(Player(i, is_ai=False))
			else:
				self.players.append(AIPlayer(i))

	def start_game(self) -> None:
		"""新規対局を開始"""
		self.wall = build_wall()
		self.current_turn = 0
		self.is_game_over = False

		# 各プレイヤーに13枚配牌
		for _ in range(13):
			for p in self.players:
				if self.wall:
					p.add_tile(self.wall.pop())

		# 親（プレイヤー0）に1枚多く与える
		if self.wall:
			self.players[0].add_tile(self.wall.pop())

	def get_current_player(self) -> Player:
		"""現在のターンのプレイヤーを取得"""
		return self.players[self.current_turn % self.num_players]

	def process_discard(self, discard_index: int, drew_tile: Optional[str] = None) -> Dict[str, Any]:
		"""
		現在のプレイヤー（human_player_id）の捨て牌を処理し、
		AI プレイヤーのターンを自動で進める
		
		Args:
			discard_index: 捨てる牌のインデックス
			drew_tile: プレイヤーが引いた牌（Webから提供）
		
		Returns:
			ターン処理結果の辞書
		"""
		current_player = self.players[self.human_player_id]
		
		if discard_index < 0 or discard_index >= len(current_player.hand):
			raise ValueError(f"Invalid discard index: {discard_index}")

		# 人間プレイヤーが捨てる
		discarded_tile = current_player.discard_tile(discard_index)

		# 次のプレイヤーから human_player_id までのAIターンを処理
		ai_log = []
		current_p_id = self.human_player_id
		


		# AI プレイヤーのターン処理（プレイヤー1, 2, 3）
		for _ in range(self.num_players - 1):
			current_p_id = (current_p_id + 1) % self.num_players

			# ツモ前に山札チェック
			if len(self.wall) <= 14:
				self.is_game_over = True
				break
			# ツモ
			drawn = self.wall.pop()
			self.players[current_p_id].add_tile(drawn)

			# AI プレイヤーが捨てる
			player = self.players[current_p_id]
			discard_idx = player.choose_discard()
			discarded = player.discard_tile(discard_idx)
			ai_log.append({
				'player': current_p_id,
				'discarded': discarded,
				'drawn': drawn,
				'shanten': player.get_shanten(),
			})

		# 人間プレイヤー（Player 0）のツモ（ターン終了時）
		player0_draw = None
		if len(self.wall) <= 14:
			self.is_game_over = True
		else:
			player0_draw = self.wall.pop()
			current_player.add_tile(player0_draw)

		# ターン数を進める
		self.current_turn += 1

		# ゲーム終了判定
		if len(self.wall) <= 14:
			self.is_game_over = True

		return {
			'discarded_tile': discarded_tile,
			'drawn_tile': None,
			'player0_draw': player0_draw,
			'auto_log': ai_log,
			'wall_count': len(self.wall),
			'is_game_over': self.is_game_over,
			'remaining_draws': max(len(self.wall) - 14, 0),
		}

	def to_dict(self) -> Dict[str, Any]:
		"""ゲーム状態を辞書化"""
		return {
			'current_turn': self.current_turn,
			'is_game_over': self.is_game_over,
			'wall_count': len(self.wall),
			'players': [p.to_dict() for p in self.players],
		}

	def to_json_serializable(self) -> Dict[str, Any]:
		"""JSON化できる辞書形式で返す（Flaskで使用）"""
		return {
			'current_turn': self.current_turn,
			'is_game_over': self.is_game_over,
			'wall': self.wall,
			'wall_count': len(self.wall),
			'players': [
				{
					'player_id': p.player_id,
					'hand': p.hand.to_list(),
					'shanten': p.get_shanten(),
					'discards': p.discards,
					'is_ai': p.is_ai,
				}
				for p in self.players
			],
		}

	def check_agari(self, player_id: int) -> bool:
		"""
		指定プレイヤーがアガり形かどうかを判定
		
		Args:
			player_id: プレイヤーID
		
		Returns:
			アガり形なら True
		"""
		if player_id < 0 or player_id >= len(self.players):
			return False
		
		player = self.players[player_id]
		return player.hand.is_winning()

	def estimate_agari_value(
		self,
		player_id: int,
		win_tile: str,
		is_tsumo: bool = True,
	) -> Dict[str, Any]:
		"""
		プレイヤーのアガり成功時の手数を計算
		
		Args:
			player_id: プレイヤーID
			win_tile: アガり牌
			is_tsumo: ツモ和了かどうか
		
		Returns:
			手数計算結果（is_winning の詳細）
		"""
		if player_id < 0 or player_id >= len(self.players):
			return {
				'valid': False,
				'error': 'プレイヤーIDが無効です',
				'han': 0,
				'fu': 0,
				'cost': {'main': 0},
				'limit': 'なし',
				'yaku': [],
			}
		
		player = self.players[player_id]
		is_dealer = (player_id == 0)  # 親判定（プレイヤー0）
		
		return player.hand.estimate_win_value(win_tile, is_tsumo, is_dealer)

	def check_and_calculate_win(
		self, player_id: int, win_tile: str, is_tsumo: bool = True
	) -> Dict[str, Any]:
		"""
		プレイヤーのアガりをチェックして点数を計算
		
		Args:
			player_id: プレイヤーID
			win_tile: アガり牌
			is_tsumo: ツモ和了かどうか
		
		Returns:
			{
				'agari': bool,
				'value': Dict,
			}
		"""
		is_agari = self.check_agari(player_id)
		
		return {
			'agari': is_agari,
			'player_id': player_id,
			'win_tile': win_tile,
			'value': self.estimate_agari_value(player_id, win_tile, is_tsumo) if is_agari else None,
		}
