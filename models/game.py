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
		self.phase: str = 'discard'  # discard | call_wait
		self.pending_calls: List[Dict[str, Any]] = []
		self.passed_callers: List[int] = []
		self._initialize_players()
		# 鳴き判定用の状態
		self.current_discarder_id: Optional[int] = None
		self.current_candidates: List[int] = []
		self.current_candidate_idx: int = 0
		self.received_calls: Dict[str, Dict[str, Any]] = {}
		self.ippatsu_eligible: List[bool] = [False] * self.num_players
		self.riichi_locked_hands: List[Optional[List[str]]] = [None] * self.num_players
		self.riichi_wait_tiles: List[List[str]] = [[] for _ in range(self.num_players)]

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
		self.last_discarded = None
		self.phase = 'discard'
		self.pending_calls = []
		self.passed_callers = []
		self.current_discarder_id = None
		self.received_calls = {}
		self.ippatsu_eligible = [False] * self.num_players
		self.riichi_locked_hands = [None] * self.num_players
		self.riichi_wait_tiles = [[] for _ in range(self.num_players)]

		# 王牌（dead_wall）を山札の最後14枚から切り出す
		self.dead_wall = full_wall[-14:]
		self.wall = full_wall[:-14]

		# ドラ表示牌（王牌の5枚目、インデックス4）
		self.dora_indicator = self.dead_wall[4] if len(self.dead_wall) >= 5 else None

		# 裏ドラ表示牌（通常はドラ表示牌の隣、インデックス5）
		self.ura_dora_indicator = self.dead_wall[5] if len(self.dead_wall) >= 6 else None

		# 各プレイヤーに13枚配牌
		for _ in range(13):
			for p in self.players:
				if self.wall:
					p.add_tile(self.wall.pop())

		# 親（プレイヤー0）に1枚多く与える
		if self.wall:
			self.players[0].add_tile(self.wall.pop())

	def _build_call_options(self, discarder_id: int, discarded_tile: str) -> List[Dict[str, Any]]:
		"""捨て牌に対する鳴き候補（プレイヤー別）を作成"""
		raw_options: List[Dict[str, Any]] = []
		next_player = (discarder_id + 1) % self.num_players

		for i in range(1, self.num_players):
			pid = (discarder_id + i) % self.num_players
			player = self.players[pid]
			player_melds = self.players[pid].melds
			calls = {
				'can_pong': self._call_checker.can_pong(player.hand.to_list(), discarded_tile),
				'can_kan': self._call_checker.can_kan(player.hand.to_list(), discarded_tile),
				'can_ron': self._call_checker.can_ron(
					player.hand.to_list(),
					discarded_tile,
					self._agari_checker,
					melds=player_melds,
				),
				'can_chow': False,
			}

			# リーチ中はロン以外の行動不可
			if getattr(player, 'is_riichi', False):
				calls['can_pong'] = False
				calls['can_kan'] = False
				calls['can_chow'] = False

			chow_combos: List[List[str]] = []
			if pid == next_player and not getattr(player, 'is_riichi', False):
				calls['can_chow'] = self._call_checker.can_chow(player.hand.to_list(), discarded_tile)
				if calls['can_chow']:
					chow_combos = self.find_chow_combinations(pid, discarded_tile)

			if any([calls['can_pong'], calls['can_kan'], calls['can_ron'], calls['can_chow']]):
				raw_options.append({
					'player_id': pid,
					'calls': calls,
					'chow_combos': chow_combos,
				})

		if not raw_options:
			return []
		return raw_options

	def _advance_turn_after_no_call(self) -> Optional[str]:
		"""鳴きなし確定後に次プレイヤーへ進めてツモ。引いた牌を返す。"""
		self.current_turn = (self.current_turn + 1) % self.num_players
		if not self.wall:
			self.is_game_over = True
			return None

		drawn_tile = self.wall.pop()
		self.players[self.current_turn].add_tile(drawn_tile)
		return drawn_tile

	def _can_tsumo_with_drawn_tile(self, player_id: int, drawn_tile: str) -> bool:
		"""リーチ時に固定した待ち牌と照合してツモ和了可能か判定。"""
		if player_id < 0 or player_id >= len(self.players):
			return False

		# リーチ時に固定した待ち牌がある場合はそれを優先する
		if self.riichi_wait_tiles[player_id]:
			return drawn_tile in self.riichi_wait_tiles[player_id]

		player = self.players[player_id]
		melds = self._agari_checker.meld_strings_to_objects(player.melds)
		winds = [EAST, SOUTH, WEST, NORTH]
		player_wind = winds[player_id % len(winds)]
		return self._agari_checker.can_win(
			hand_tiles=player.hand.to_list(),
			win_tile=drawn_tile,
			melds=melds,
			is_tsumo=True,
			player_wind=player_wind,
			round_wind=self.round_wind,
		)

	def _compute_wait_tiles_from_hand(self, hand_tiles: List[str], melds: List[List[str]]) -> List[str]:
		"""13枚手牌（＋副露）から待ち牌一覧を算出する。"""
		candidates = ['1m','2m','3m','4m','5m','6m','7m','8m','9m',
					  '1p','2p','3p','4p','5p','6p','7p','8p','9p',
					  '1s','2s','3s','4s','5s','6s','7s','8s','9s',
					  'E','S','W','N','P','F','C']
		winners: List[str] = []
		for candidate in candidates:
			if self._agari_checker.is_agari(hand_tiles + [candidate], melds=melds):
				winners.append(candidate)
		return winners

	def _auto_discard_after_riichi_if_needed(self, drawn_tile: Optional[str]) -> Dict[str, Any]:
		"""リーチ者のツモ後、非和了牌なら自動ツモ切りして必要なら鳴き待ちへ遷移。"""
		auto_log: List[Dict[str, Any]] = []

		while drawn_tile is not None and not self.is_game_over:
			pid = self.current_turn
			player = self.players[pid]
			if not getattr(player, 'is_riichi', False):
				break

			if self._can_tsumo_with_drawn_tile(pid, drawn_tile):
				# 和了牌を引いた場合は自動打牌せず、UIからアガり判定できるように止める
				break

			hand_list = player.hand.to_list()
			if drawn_tile in hand_list:
				discard_idx = max(i for i, t in enumerate(hand_list) if t == drawn_tile)
			else:
				discard_idx = len(player.hand) - 1
			discarded_tile = player.discard_tile(discard_idx)
			self.ippatsu_eligible[pid] = False
			self.last_discarded = discarded_tile
			self.current_discarder_id = pid
			self.passed_callers = []
			self.received_calls = {}
			auto_log.append({'player': pid, 'discarded': discarded_tile})

			available_calls = self._build_call_options(pid, discarded_tile)
			if available_calls:
				self.phase = 'call_wait'
				self.pending_calls = available_calls
				return {
					'awaiting_call': True,
					'available_calls': available_calls,
					'discarded_tile': discarded_tile,
					'discarder_id': pid,
					'auto_log': auto_log,
				}

			drawn_tile = self._advance_turn_after_no_call()
			self.phase = 'discard'
			self.pending_calls = []
			self.last_discarded = None
			self.current_discarder_id = None

		return {
			'awaiting_call': False,
			'next_draw': drawn_tile,
			'auto_log': auto_log,
		}

	def get_current_player(self) -> Player:
		"""現在のターンのプレイヤーを取得"""
		return self.players[self.current_turn % self.num_players]

	def process_discard(self, discard_index: int, drew_tile: Optional[str] = None, declare_riichi: bool = False) -> Dict[str, Any]:
		"""
		現在ターンのプレイヤーの打牌を処理し、鳴き割り込みを判定する。
		
		Args:
			discard_index: 捨てる牌のインデックス
			drew_tile: プレイヤーが引いた牌（Webから提供）
			declare_riichi: リーチ宣言かどうか
		
		Returns:
			ターン処理結果の辞書
		"""
		if self.is_game_over:
			return {'error': 'Game is already over', 'is_game_over': True}

		if self.phase == 'call_wait':
			return {
				'error': 'Call resolution is pending',
				'awaiting_call': True,
				'available_calls': self.pending_calls,
				'discarded_tile': self.last_discarded,
			}

		current_player = self.get_current_player()
		discarder_id = self.current_turn

		# リーチ後は自動ツモ切り（ツモ牌を自動で捨てる）
		if current_player.is_riichi and drew_tile is not None:
			hand_list = current_player.hand.to_list()
			if drew_tile in hand_list:
				discard_index = max(i for i, t in enumerate(hand_list) if t == drew_tile)
			else:
				discard_index = len(current_player.hand) - 1

		if discard_index < 0 or discard_index >= len(current_player.hand):
			raise ValueError(f"Invalid discard index: {discard_index}")

		# リーチ宣言があれば状態を更新
		if declare_riichi:
			current_player.is_riichi = True
			self.ippatsu_eligible[discarder_id] = True
		elif current_player.is_riichi:
			# リーチ後最初の自摸番を消化したら一発権は消える
			self.ippatsu_eligible[discarder_id] = False

		discarded_tile = current_player.discard_tile(discard_index)
		if declare_riichi:
			self.riichi_locked_hands[discarder_id] = current_player.hand.to_list()
			self.riichi_wait_tiles[discarder_id] = self._compute_wait_tiles_from_hand(
				self.riichi_locked_hands[discarder_id],
				current_player.melds,
			)
		self.last_discarded = discarded_tile
		self.current_discarder_id = discarder_id
		self.passed_callers = []
		self.received_calls = {}

		available_calls = self._build_call_options(discarder_id, discarded_tile)
		if available_calls:
			self.phase = 'call_wait'
			self.pending_calls = available_calls
			return {
				'discarded_tile': discarded_tile,
				'discarder_id': discarder_id,
				'available_calls': available_calls,
				'awaiting_call': True,
				'current_turn': self.current_turn,
				'wall_count': len(self.wall),
				'is_game_over': self.is_game_over,
				'remaining_draws': max(len(self.wall), 0),
			}
		# available_callsがなければ次のプレイヤーがツモる

		drawn = self._advance_turn_after_no_call()
		self.phase = 'discard'
		self.pending_calls = []
		self.last_discarded = None
		self.current_discarder_id = None
		auto_result = self._auto_discard_after_riichi_if_needed(drawn)

		return {
			'discarded_tile': auto_result.get('discarded_tile', discarded_tile),
			'discarder_id': auto_result.get('discarder_id', discarder_id),
			'available_calls': auto_result.get('available_calls', []),
			'awaiting_call': auto_result.get('awaiting_call', False),
			'next_draw': auto_result.get('next_draw', drawn),
			'auto_log': auto_result.get('auto_log', []),
			'current_turn': self.current_turn,
			'wall_count': len(self.wall),
			'is_game_over': self.is_game_over,
			'remaining_draws': max(len(self.wall), 0),
		}

	def resolve_pending_call(self, player_id: int, action: str, tiles: Optional[List[str]] = None) -> Dict[str, Any]:
		"""待機中の鳴き割り込みに対する入力を蓄積し、全員分揃ったら解決する"""
		tiles = tiles or []
		if self.is_game_over:
			return {'ok': False, 'error': 'Game is already over'}
		if self.phase != 'call_wait' or not self.pending_calls:
			return {'ok': False, 'error': 'No pending call'}

		entry = next((item for item in self.pending_calls if item['player_id'] == player_id), None)
		if entry is None:
			return {'ok': False, 'error': 'Player is not eligible for current call'}

		if getattr(self.players[player_id], 'is_riichi', False) and action not in ['ron', 'pass']:
			return {'ok': False, 'error': 'Riichi player can only choose ron or pass'}

		# 返答を記録 (JSON互換のためplayer_idは文字列キーにする)
		self.received_calls[str(player_id)] = {'action': action, 'tiles': tiles}

		# 鳴きの権利を持つ全員から返答が来たかチェック
		pending_player_ids = {str(item['player_id']) for item in self.pending_calls}
		if set(self.received_calls.keys()) != pending_player_ids:
			# まだ返答していないプレイヤーのUIだけを残すためのリスト作成
			remaining_calls = [c for c in self.pending_calls if str(c['player_id']) not in self.received_calls]
			return {
				'ok': True,
				'action': 'waiting',
				'awaiting_call': True,
				'available_calls': remaining_calls,
				'discarded_tile': self.last_discarded,
				'current_turn': self.current_turn,
			}

		# 全員の返答が揃ったため優先順位に従って実行
		return self._execute_highest_priority_call()

	def _execute_highest_priority_call(self) -> Dict[str, Any]:
		"""蓄積された返答から優先順位（ロン > ポン/カン > チー）を判定して実行する"""
		ron_calls = {pid: data for pid, data in self.received_calls.items() if data['action'] == 'ron'}
		pon_kan_calls = {pid: data for pid, data in self.received_calls.items() if data['action'] in ['pong', 'kan']}
		chow_calls = {pid: data for pid, data in self.received_calls.items() if data['action'] == 'chow'}

		action_taken = 'pass'
		response_data = {}

		if ron_calls:
			print("[DEBUG] _execute_highest_priority_call: RON called")
			winner_id = int(list(ron_calls.keys())[0])
			winner = self.players[winner_id]
			is_winner_riichi = bool(getattr(winner, 'is_riichi', False))
			value = self.estimate_agari_value(
				winner_id,
				self.last_discarded,
				is_tsumo=False,
				is_riichi=is_winner_riichi,
				is_ippatsu=self.ippatsu_eligible[winner_id],
			)
			self.is_game_over = True
			response_data = {
				'ok': True, 'action': 'ron', 'is_game_over': True, 'agari': True,
				'type': 'ron', 'player_id': winner_id, 'win_tile': self.last_discarded, 'value': value,
			}
			if is_winner_riichi and len(self.dead_wall) >= 6:
				response_data['ura_dora_indicator'] = self.dead_wall[5]
		elif pon_kan_calls:
			self.ippatsu_eligible = [False] * self.num_players
			pid = int(list(pon_kan_calls.keys())[0])
			data = pon_kan_calls[str(pid)]
			if data['action'] == 'pong':
				self.apply_pong(pid, [self.last_discarded, self.last_discarded, self.last_discarded])
			else:
				self.apply_kan(pid, self.last_discarded, is_closed=False)
			action_taken = data['action']
		elif chow_calls:
			self.ippatsu_eligible = [False] * self.num_players
			pid = int(list(chow_calls.keys())[0])
			data = chow_calls[str(pid)]
			tiles = data['tiles'] if data['tiles'] else self.find_chow_combinations(pid, self.last_discarded)[0]
			self.apply_chow(pid, tiles)
			action_taken = 'chow'
		else:
			drawn = self._advance_turn_after_no_call()
			auto_result = self._auto_discard_after_riichi_if_needed(drawn)
			action_taken = 'pass'
			response_data = {
				'ok': True, 'action': 'pass',
				'awaiting_call': auto_result.get('awaiting_call', False),
				'available_calls': auto_result.get('available_calls', []),
				'discarded_tile': auto_result.get('discarded_tile'),
				'discarder_id': auto_result.get('discarder_id'),
				'next_draw': auto_result.get('next_draw', drawn),
				'auto_log': auto_result.get('auto_log', []),
				'current_turn': self.current_turn, 'is_game_over': self.is_game_over,
				'wall_count': len(self.wall), 'remaining_draws': max(len(self.wall), 0),
			}

		is_awaiting_new_call = bool(response_data.get('awaiting_call', False))
		if not is_awaiting_new_call:
			self.phase = 'discard'
			self.pending_calls = []
			self.last_discarded = None
			self.current_discarder_id = None
		self.received_calls = {}

		if not response_data:
			response_data = {
				'ok': True, 'action': action_taken, 'awaiting_call': False, 'available_calls': [],
				'current_turn': self.current_turn, 'is_game_over': self.is_game_over,
				'wall_count': len(self.wall), 'remaining_draws': max(len(self.wall), 0),
			}

		return response_data

	def to_dict(self) -> Dict[str, Any]:
		"""ゲーム状態を辞書化"""
		return {
			'current_turn': self.current_turn,
			'is_game_over': self.is_game_over,
			'wall_count': len(self.wall),
			'players': [p.to_dict() for p in self.players],
		}

	def to_json_serializable(self) -> Dict[str, Any]:
		"""JSON化できる辞書形式で返す(Flaskで使用)"""
		return {
			'current_turn': self.current_turn,
			'is_game_over': self.is_game_over,
			'phase': self.phase,
			'last_discarded': self.last_discarded,
			'pending_calls': self.pending_calls,
			'passed_callers': self.passed_callers,
			'current_discarder_id': self.current_discarder_id,
			'wall': self.wall,
			'wall_count': len(self.wall),
			'dora_indicator': self.dora_indicator,
			'ura_dora_indicator': getattr(self, 'ura_dora_indicator', None),
			'dead_wall': self.dead_wall,
			'round_wind': self.round_wind,
			'players': [
				{
					'player_id': p.player_id,
					'hand': p.hand.to_list(),
					'shanten': p.get_shanten(),
					'discards': p.discards,
					'melds': p.melds,
					'is_ai': p.is_ai,
					'is_riichi': getattr(p, 'is_riichi', False)
				}
				for p in self.players
			],
			'ippatsu_eligible': self.ippatsu_eligible,
			'riichi_locked_hands': self.riichi_locked_hands,
			'riichi_wait_tiles': self.riichi_wait_tiles,
			'received_calls': self.received_calls,
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
		melds = self._agari_checker.meld_strings_to_objects(player.melds)
		if not player.hand.to_list():
			return False
		for win_tile in set(player.hand.to_list()):
			if self._agari_checker.can_win(player.hand.to_list(), win_tile, melds=melds, is_tsumo=True):
				return True
		return False

	def estimate_agari_value(
		self,
		player_id: int,
		win_tile: str,
		is_tsumo: bool = True,
		is_riichi: bool = False,
		is_ippatsu: Optional[bool] = None,
	) -> Dict[str, Any]:
		"""
		プレイヤーのアガり成功時の手数を計算
		
		Args:
			player_id: プレイヤーID
			win_tile: アガり牌
			is_tsumo: ツモ和了かどうか
		
		Returns:
			手数計算結果(is_winning の詳細）
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
		melds = self._agari_checker.meld_strings_to_objects(player.melds)
		
		# 自風を計算（プレイヤーIDを基に）
		winds = [EAST, SOUTH, WEST, NORTH]
		player_wind = winds[player_id % len(winds)]  # プレイヤー0→EAST, 1→SOUTH, ...
		
		# ドラ表示牌・裏ドラ表示牌をリストに変換
		dora_indicators = []
		ura_dora = None
		if self.dead_wall and len(self.dead_wall) >= 5:
			dora_indicators.append(self.dead_wall[4])
		# リーチ状態でアガった場合のみ裏ドラを加算（dead_wall[5]）
		if is_riichi and self.dead_wall and len(self.dead_wall) >= 6:
			ura_dora = self.dead_wall[5]
			dora_indicators.append(ura_dora)
		print(f"[DEBUG] estimate_agari_value: ura_dora={ura_dora} (dead_wall={self.dead_wall})")
		if not dora_indicators:
			dora_indicators = None
		effective_is_ippatsu = bool(
			(self.ippatsu_eligible[player_id] if is_ippatsu is None else is_ippatsu)
			and is_riichi
		)
		return player.hand.estimate_win_value(
			win_tile, is_tsumo, is_dealer,
			melds=melds,
			player_wind=player_wind, round_wind=self.round_wind,
			dora_indicators=dora_indicators,
			is_riichi=is_riichi,
			is_ippatsu=effective_is_ippatsu,
		)

	def check_and_calculate_win(
		self, player_id: int, win_tile: str, is_tsumo: bool = True, is_riichi: bool = False
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
				'ura_dora_indicator': str | None
			}
		"""
		print("[DEBUG] check_and_calculate_win called")
		is_agari = self.check_agari(player_id)
		player = self.players[player_id]
		actual_is_riichi = getattr(player, 'is_riichi', False) or is_riichi
		result = {
			'agari': is_agari,
			'player_id': player_id,
			'win_tile': win_tile,
			'value': self.estimate_agari_value(
				player_id,
				win_tile,
				is_tsumo,
				actual_is_riichi,
				self.ippatsu_eligible[player_id],
			) if is_agari else None,
		}
		# 王牌リストから直接裏ドラ表示牌（インデックス5）を取得する
		if is_agari and actual_is_riichi:
			result['ura_dora_indicator'] = self.dead_wall[5] if len(self.dead_wall) >= 6 else None
		return result

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
		player_melds = player.melds
		
		# チーが可能な場合は番のプレイヤーチェック（捨てたプレイヤーの ディーラー番の次 までが可能）
		can_chow = False
		
		# ロン判定
		can_ron = self._call_checker.can_ron(hand_tiles, discarded_tile, self._agari_checker, melds=player_melds)

		if getattr(player, 'is_riichi', False):
			return {
				'can_pong': False,
				'can_chow': False,
				'can_ron': can_ron,
			}
		
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
		if getattr(player, 'is_riichi', False):
			return False

		# 明槓の場合は最後の捨て牌が対象であるべき
		if not is_closed and self.last_discarded != tile:
			return False
		ok = player.call_kan(tile, is_closed=is_closed)
		if ok:
			self.ippatsu_eligible = [False] * self.num_players
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
		if getattr(self.players[player_id], 'is_riichi', False):
			return False

		ok = self.players[player_id].call_pong(tiles)
		if ok:
			self.ippatsu_eligible = [False] * self.num_players
			self.current_turn = player_id
			self.last_discarded = None
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
		if getattr(self.players[player_id], 'is_riichi', False):
			return False
		if self.last_discarded is None:
			return False

		ok = self.players[player_id].call_chow(tiles, discarded_tile=self.last_discarded)
		if ok:
			self.ippatsu_eligible = [False] * self.num_players
			self.current_turn = player_id
			self.last_discarded = None
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
				'value': Dict (ロンが可能な場合),
			}
		"""
		if player_id < 0 or player_id >= len(self.players):
			return {'can_ron': False, 'value': None}
		
		can_ron = self._call_checker.can_ron(
			self.players[player_id].hand.to_list(),
			discarded_tile,
			self._agari_checker,
			melds=self.players[player_id].melds,
		)
		
		if not can_ron:
			return {'can_ron': False, 'value': None}
		
		# ロンの場合は is_tsumo=False
		player = self.players[player_id]
		value = self.estimate_agari_value(
			player_id,
			discarded_tile,
			is_tsumo=False,
			is_riichi=getattr(player, 'is_riichi', False),
			is_ippatsu=self.ippatsu_eligible[player_id],
		)
		
		return {
			'can_ron': True,
			'player_id': player_id,
			'discarded_tile': discarded_tile,
			'value': value,
		}

	def get_agari_tiles(self, player_id: int) -> List[str]:
		"""指定プレイヤーの待ち牌(アガリ牌)一覧を返す。"""
		if player_id < 0 or player_id >= len(self.players):
			return []

		player = self.players[player_id]
		hand_tiles = player.hand.to_list()
		melds = player.melds

		# 副露分を除いた暗部の期待枚数（14 - 副露枚数）
		meld_tiles_count = sum(len(m) for m in melds)
		expected_concealed = 14 - meld_tiles_count

		# 待ち判定できるのは、暗部が期待枚数-1（ロン/ツモ1枚待ち）のとき
		if len(hand_tiles) != expected_concealed - 1:
			return []

		winners: List[str] = []
		for candidate in ['1m','2m','3m','4m','5m','6m','7m','8m','9m',
					   '1p','2p','3p','4p','5p','6p','7p','8p','9p',
					   '1s','2s','3s','4s','5s','6s','7s','8s','9s',
					   'E','S','W','N','P','F','C']:
			trial = hand_tiles + [candidate]
			if self._agari_checker.is_agari(trial, melds=melds):
				winners.append(candidate)

		return winners
