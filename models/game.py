"""
ゲーム全体の管理
"""
from typing import List, Optional, Dict, Any

from models.tile_utils import build_wall
from models.player import Player, AIPlayer
from logic.agari import AgariChecker
from logic.calls import CallChecker, CallAction
from mahjong.constants import EAST, SOUTH, WEST, NORTH



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
		self.dead_wall: List[str] = []  # 王牌
		self.dora_indicator: Optional[str] = None  # ドラ表示牌
		self.round_wind: int = EAST  # 場風（mahjong.constants の EAST/SOUTH/... を使用）
		self.current_turn = 0
		self.is_game_over = False
		self._agari_checker = AgariChecker()
		self._call_checker = CallChecker()
		self.last_discarded: Optional[str] = None
		self._initialize_players()
		# 鳴き判定用の状態
		self.current_discarder_id: Optional[int] = None
		self.current_candidates: List[int] = []
		self.current_candidate_idx: int = 0

	def _initialize_players(self) -> None:
		"""プレイヤーを初期化"""
		for i in range(self.num_players):
			if i == self.human_player_id:
				self.players.append(Player(i, is_ai=False))
			else:
				self.players.append(AIPlayer(i))

	def start_game(self) -> None:
		"""新規対局を開始"""
		full_wall = build_wall()
		self.current_turn = 0
		self.is_game_over = False

		# 王牌（dead_wall）を山札の最後14枚から切り出す
		self.dead_wall = full_wall[-14:]
		self.wall = full_wall[:-14]

		# ドラ表示牌（王牌の5枚目、インデックス4）
		self.dora_indicator = self.dead_wall[4] if len(self.dead_wall) >= 5 else None

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
		# 初期の捨て牌（通常は人間の捨て）
		current_player = self.players[self.human_player_id]
		if discard_index < 0 or discard_index >= len(current_player.hand):
			raise ValueError(f"Invalid discard index: {discard_index}")

		# perform discard
		discarded_tile = current_player.discard_tile(discard_index)
		self.last_discarded = discarded_tile
		self.current_discarder_id = current_player.player_id
		# build candidate list (next players in turn order)
		candidates = []
		for i in range(1, self.num_players):
			pid = (self.current_discarder_id + i) % self.num_players
			candidates.append(pid)
		self.current_candidates = candidates
		self.current_candidate_idx = 0

		# 1) Check ron across all candidates
		for pid in candidates:
			if self._call_checker.can_ron(self.players[pid].hand.to_list(), self.last_discarded, self._agari_checker):
				# if human, return for front-end decision
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_ron'] = True
					self.current_candidate_idx = candidates.index(pid)
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				# AI auto-ron
				value = self.estimate_agari_value(pid, self.last_discarded, is_tsumo=False)
				self.is_game_over = True
				return {'agari': True, 'type': 'ron', 'player_id': pid, 'win_tile': self.last_discarded, 'value': value}

		# 2) Sequentially check kan/pong for each candidate in order
		for idx, pid in enumerate(candidates):
			# check kan
			if self._call_checker.can_kan(self.players[pid].hand.to_list(), self.last_discarded):
				# human: present options
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_kan'] = True
					self.current_candidate_idx = idx
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				# AI: auto kan
				ok = self.apply_kan(pid, self.last_discarded, is_closed=False)
				if ok:
					# AI should immediately discard
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						# start new call sequence from this new discard
						return self.process_discard_auto_from(pid)

			# check pong
			if self._call_checker.can_pong(self.players[pid].hand.to_list(), self.last_discarded):
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_pong'] = True
					self.current_candidate_idx = idx
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				# AI pong
				ok = self.apply_pong(pid, [self.last_discarded]*3)
				if ok:
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(pid)

		# 3) Check chow only for next player
		next_player = candidates[0]
		if self._call_checker.can_chow(self.players[next_player].hand.to_list(), self.last_discarded):
			if next_player == self.human_player_id:
				calls = self.check_available_calls(next_player, self.last_discarded)
				calls['can_chow'] = True
				self.current_candidate_idx = 0
				return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': next_player, 'calls': calls, 'chow_combos': self.find_chow_combinations(next_player, self.last_discarded)}], 'awaiting_human': True}
			# AI chow
			combos = self.find_chow_combinations(next_player, self.last_discarded)
			if combos:
				ok = self.apply_chow(next_player, combos[0])
				if ok:
					caller = self.players[next_player]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(next_player)

		# nobody called: advance normal turn to next player (the one after discarder)
		next_turn = (self.current_discarder_id + 1) % self.num_players
		self.current_turn = next_turn
		# draw for next player if wall
		if not self.wall:
			self.is_game_over = True
			return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': None, 'auto_log': []}
		drawn = self.wall.pop()
		self.players[next_turn].add_tile(drawn)
		# return info so frontend can update
		return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': drawn, 'auto_log': []}


	def process_discard_auto_from(self, discarder_id: int) -> Dict[str, Any]:
		"""
		Helper called when an AI has claimed and then discarded: continue processing from that new discard.
		"""
		candidates = []
		for i in range(1, self.num_players):
			pid = (discarder_id + i) % self.num_players
			candidates.append(pid)
		# check ron
		for pid in candidates:
			if self._call_checker.can_ron(self.players[pid].hand.to_list(), self.last_discarded, self._agari_checker):
				value = self.estimate_agari_value(pid, self.last_discarded, is_tsumo=False)
				self.is_game_over = True
				return {'agari': True, 'type': 'ron', 'player_id': pid, 'win_tile': self.last_discarded, 'value': value}
		# check kan/pong sequentially
		for pid in candidates:
			if self._call_checker.can_kan(self.players[pid].hand.to_list(), self.last_discarded):
				ok = self.apply_kan(pid, self.last_discarded, is_closed=False)
				if ok:
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(pid)
			if self._call_checker.can_pong(self.players[pid].hand.to_list(), self.last_discarded):
				ok = self.apply_pong(pid, [self.last_discarded]*3)
				if ok:
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(pid)
		# check chow for next player
		next_player = candidates[0]
		if self._call_checker.can_chow(self.players[next_player].hand.to_list(), self.last_discarded):
			combos = self.find_chow_combinations(next_player, self.last_discarded)
			if combos:
				ok = self.apply_chow(next_player, combos[0])
				if ok:
					caller = self.players[next_player]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(next_player)
		# nobody called: advance
		next_turn = (discarder_id + 1) % self.num_players
		self.current_turn = next_turn
		if not self.wall:
			self.is_game_over = True
			return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': None, 'auto_log': []}
		drawn = self.wall.pop()
		self.players[next_turn].add_tile(drawn)
		return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': drawn, 'auto_log': []}

	def continue_call_sequence(self) -> Dict[str, Any]:
		"""Continue the call sequence after a human 'pass'. Uses stored current_candidates and current_candidate_idx."""
		if not self.current_candidates:
			return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': None}
		start = self.current_candidate_idx + 1
		candidates = self.current_candidates
		# check remaining candidates for ron first
		for pid in candidates[start:]:
			if self._call_checker.can_ron(self.players[pid].hand.to_list(), self.last_discarded, self._agari_checker):
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_ron'] = True
					self.current_candidate_idx = candidates.index(pid)
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				value = self.estimate_agari_value(pid, self.last_discarded, is_tsumo=False)
				self.is_game_over = True
				return {'agari': True, 'type': 'ron', 'player_id': pid, 'win_tile': self.last_discarded, 'value': value}

		# then sequentially check kan/pong
		for idx in range(start, len(candidates)):
			pid = candidates[idx]
			if self._call_checker.can_kan(self.players[pid].hand.to_list(), self.last_discarded):
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_kan'] = True
					self.current_candidate_idx = idx
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				ok = self.apply_kan(pid, self.last_discarded, is_closed=False)
				if ok:
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(pid)

			if self._call_checker.can_pong(self.players[pid].hand.to_list(), self.last_discarded):
				if pid == self.human_player_id:
					calls = self.check_available_calls(pid, self.last_discarded)
					calls['can_pong'] = True
					self.current_candidate_idx = idx
					return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': pid, 'calls': calls, 'chow_combos': []}], 'awaiting_human': True}
				ok = self.apply_pong(pid, [self.last_discarded]*3)
				if ok:
					caller = self.players[pid]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(pid)

		# if we reach the end, check chow for next player if not already checked
		# next player is candidates[0]
		next_player = candidates[0]
		if self._call_checker.can_chow(self.players[next_player].hand.to_list(), self.last_discarded):
			if next_player == self.human_player_id:
				calls = self.check_available_calls(next_player, self.last_discarded)
				calls['can_chow'] = True
				self.current_candidate_idx = 0
				return {'discarded_tile': self.last_discarded, 'available_calls': [{'player_id': next_player, 'calls': calls, 'chow_combos': self.find_chow_combinations(next_player, self.last_discarded)}], 'awaiting_human': True}
			combos = self.find_chow_combinations(next_player, self.last_discarded)
			if combos:
				ok = self.apply_chow(next_player, combos[0])
				if ok:
					caller = self.players[next_player]
					if caller.is_ai:
						discard_idx = caller.choose_discard()
						discarded = caller.discard_tile(discard_idx)
						self.last_discarded = discarded
						return self.process_discard_auto_from(next_player)

		# nobody claimed -> advance to next player's draw
		next_turn = (self.current_discarder_id + 1) % self.num_players
		self.current_turn = next_turn
		if not self.wall:
			self.is_game_over = True
			return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': None, 'auto_log': []}
		drawn = self.wall.pop()
		self.players[next_turn].add_tile(drawn)
		return {'discarded_tile': self.last_discarded, 'available_calls': [], 'player0_draw': drawn, 'auto_log': []}
				self.players[self.human_player_id].add_tile(player0_draw)

			# ターン数を進める
			self.current_turn += 1

			# ゲーム終了判定
			if not self.wall:
				self.is_game_over = True

			return {
				'discarded_tile': discarded_tile,
				'drawn_tile': None,
				'player0_draw': player0_draw,
				'auto_log': ai_log,
				'wall_count': len(self.wall),
				'is_game_over': self.is_game_over,
				'remaining_draws': max(len(self.wall), 0),
			}

		# 鳴きがあった場合はそのログと最新のlast_discarded情報を返す
		return {
			'discarded_tile': discarded_tile,
			'last_discarded': self.last_discarded,
			'auto_log': auto_log,
			'wall_count': len(self.wall),
			'is_game_over': self.is_game_over,
			'remaining_draws': max(len(self.wall), 0),
		}

		# 人間プレイヤー（Player 0）のツモ（ターン終了時）
		player0_draw = None
		if not self.wall:
			self.is_game_over = True
		else:
			player0_draw = self.wall.pop()
			current_player.add_tile(player0_draw)

		# ターン数を進める
		self.current_turn += 1

		# ゲーム終了判定
		if not self.wall:
			self.is_game_over = True

		return {
			'discarded_tile': discarded_tile,
			'drawn_tile': None,
			'player0_draw': player0_draw,
			'auto_log': ai_log,
			'wall_count': len(self.wall),
			'is_game_over': self.is_game_over,
			'remaining_draws': max(len(self.wall), 0),
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
			'dora_indicator': self.dora_indicator,
			'round_wind': self.round_wind,
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
		
		# 自風を計算（プレイヤーIDを基に）
		winds = [EAST, SOUTH, WEST, NORTH]
		player_wind = winds[player_id % len(winds)]  # プレイヤー0→EAST, 1→SOUTH, ...
		
		# ドラ表示牌をリストに変換
		dora_indicators = [self.dora_indicator] if self.dora_indicator else None
		
		return player.hand.estimate_win_value(
			win_tile, is_tsumo, is_dealer,
			player_wind=player_wind, round_wind=self.round_wind,
			dora_indicators=dora_indicators
		)

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

	def check_available_calls(self, player_id: int, discarded_tile: str) -> Dict[str, bool]:
		"""
		プレイヤーが実行可能な鳴きをチェック
		
		Args:
			player_id: プレイヤーID
			discarded_tile: 捨てられた牌
		
		Returns:
			{
				'can_pong': bool,
				'can_chow': bool,
				'can_ron': bool,
			}
		"""
		if player_id < 0 or player_id >= len(self.players):
			return {'can_pong': False, 'can_chow': False, 'can_ron': False}
		
		player = self.players[player_id]
		hand_tiles = player.hand.to_list()
		
		# チーが可能な場合は番のプレイヤーチェック（捨てたプレイヤーの ディーラー番の次 までが可能）
		can_chow = False
		
		# ロン判定
		can_ron = self._call_checker.can_ron(hand_tiles, discarded_tile, self._agari_checker)
		
		return {
			'can_pong': self._call_checker.can_pong(hand_tiles, discarded_tile),
			'can_chow': self._call_checker.can_chow(hand_tiles, discarded_tile),
			'can_ron': can_ron,
		}

	def apply_kan(self, player_id: int, tile: str, is_closed: bool = False) -> bool:
		"""
		プレイヤーがカンを実行する。明槓（捨て牌利用）は is_closed=False。

		Args:
			player_id: プレイヤーID
			tile: カンに使う牌（文字列）
			is_closed: 暗槓か

		Returns:
			成功なら True
		"""
		if player_id < 0 or player_id >= len(self.players):
			return False

		player = self.players[player_id]

		# 明槓の場合は最後の捨て牌が対象であるべき
		if not is_closed and self.last_discarded != tile:
			return False

		ok = player.call_kan(tile, is_closed=is_closed)
		if ok:
			# 明槓なら捨て牌は場から消費済み（last_discarded をクリア）
			if not is_closed:
				self.last_discarded = None
			# カンをしたプレイヤーに番が移る
			self.current_turn = player_id
			# 補充牌を1枚ツモさせる（山があれば）
			if self.wall:
				repl = self.wall.pop()
				player.add_tile(repl)
				# 補充牌は process_discard の auto_log で追記される
		return ok

	def find_pong_combinations(self, player_id: int, discarded_tile: str) -> List[List[str]]:
		"""
		ポンの組み合わせを検出
		
		Args:
			player_id: プレイヤーID
			discarded_tile: 捨てられた牌
		
		Returns:
			ポンの組み合わせリスト（通常は1つ）
		"""
		if player_id < 0 or player_id >= len(self.players):
			return []
		
		player = self.players[player_id]
		
		if not self._call_checker.can_pong(player.hand.to_list(), discarded_tile):
			return []
		
		# ポンは常に1つの組み合わせのみ
		return [[discarded_tile, discarded_tile, discarded_tile]]

	def find_chow_combinations(self, player_id: int, discarded_tile: str) -> List[List[str]]:
		"""
		チーの可能な組み合わせを検出
		
		Args:
			player_id: プレイヤーID
			discarded_tile: 捨てられた牌
		
		Returns:
			チーの組み合わせリスト
		"""
		if player_id < 0 or player_id >= len(self.players):
			return []
		
		player = self.players[player_id]
		hand_tiles = player.hand.to_list()
		
		possible = CallChecker._find_possible_chows(hand_tiles, discarded_tile)
		return [list(combo) for combo in possible]

	def apply_pong(self, player_id: int, tiles: List[str]) -> bool:
		"""
		ポンを適用
		
		Args:
			player_id: プレイヤーID
			tiles: ポンを作る3つの牌
		
		Returns:
			成功なら True
		"""
		if player_id < 0 or player_id >= len(self.players):
			return False
		
		ok = self.players[player_id].call_pong(tiles)
		if ok:
			# the discarded tile has been claimed
			self.last_discarded = None
			# turn moves to caller
			self.current_turn = player_id
		return ok

	def apply_chow(self, player_id: int, tiles: List[str]) -> bool:
		"""
		チーを適用
		
		Args:
			player_id: プレイヤーID
			tiles: チーを作る3つの牌
		
		Returns:
			成功なら True
		"""
		if player_id < 0 or player_id >= len(self.players):
			return False
		
		ok = self.players[player_id].call_chow(tiles)
		if ok:
			self.last_discarded = None
			self.current_turn = player_id
		return ok

	def check_ron(self, player_id: int, discarded_tile: str) -> Dict[str, Any]:
		"""
		ロン和了をチェックして点数を計算
		
		Args:
			player_id: プレイヤーID
			discarded_tile: ロンする牌
		
		Returns:
			{
				'can_ron': bool,
				'value': Dict（ロンが可能な場合）,
			}
		"""
		if player_id < 0 or player_id >= len(self.players):
			return {'can_ron': False, 'value': None}
		
		can_ron = self._call_checker.can_ron(
			self.players[player_id].hand.to_list(),
			discarded_tile,
			self._agari_checker
		)
		
		if not can_ron:
			return {'can_ron': False, 'value': None}
		
		# ロンの場合は is_tsumo=False
		value = self.estimate_agari_value(player_id, discarded_tile, is_tsumo=False)
		
		return {
			'can_ron': True,
			'player_id': player_id,
			'discarded_tile': discarded_tile,
			'value': value,
		}
