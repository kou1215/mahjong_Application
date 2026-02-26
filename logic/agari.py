"""
アガり（和了）判定とスコア計算
mahjongライブラリを使用した訳判定と手数計算
"""
from typing import List, Dict, Optional, Any
from mahjong.agari import Agari as MahjongAgari
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.meld import Meld
from mahjong.constants import EAST, SOUTH, WEST, NORTH

from models.tile_utils import TILE_INDEX


class AgariChecker:
    """アガり判定と手数計算のラッパークラス"""
    
    # 風は mahjong.constants の EAST/SOUTH/WEST/NORTH を使用する

    def __init__(self):
        """初期化"""
        self.agari = MahjongAgari()
        self.calculator = HandCalculator()

    def is_agari(self, hand_tiles: List[str]) -> bool:
        """
        手牌がアガり形かどうかを判定
        
        Args:
            hand_tiles: 手牌のリスト（例：['1m', '1m', '2p', ...]）
        
        Returns:
            アガり形なら True、そうでなければ False
        """
        if len(hand_tiles) != 14:
            return False
        
        try:
            # リスト形式から34配列に変換
            tiles_34 = self._tiles_to_34_array(hand_tiles)
            return self.agari.is_agari(tiles_34)
        except Exception:
            return False

    def estimate_hand_value(
        self,
        hand_tiles: List[str],
        win_tile: str,
        is_tsumo: bool = True,
        is_dealer: bool = False,
        melds: Optional[List[Meld]] = None,
        player_wind: int = EAST,
        round_wind: int = EAST,
        dora_indicators: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        アガり手の点数を計算
        
        自風・場風・ドラを考慮した詳細な点数計算を行う
        
        Args:
            hand_tiles: 手牌のリスト（14枚）
            win_tile: アガり牌
            is_tsumo: ツモ和了かどうかのフラグ
            is_dealer: 親かどうかのフラグ
            melds: 鳴きのリスト
            player_wind: 自風（1:東, 2:南, 3:西, 4:北）
            round_wind: 場風（1:東, 2:南, 3:西, 4:北）
            dora_indicators: ドラ表示牌のリスト（例：['5m', '1p']）
        
        Returns:
            {
                'valid': bool,
                'error': Optional[str],
                'han': int,
                'fu': int,
                'cost': {
                    'main': int,          # 総支払い金額
                    'main_bonus': int,    # 親／子のボーナス
                    'additional': int,    # 追加支払い
                    'additional_bonus': int,
                    'kyoutaku_bonus': int,
                    'total': int
                },
                'limit': str,             # 満貫、跳満など
                'yaku': List[str],        # 成立した役のリスト
            }
        """
        if len(hand_tiles) != 14:
            return {
                'valid': False,
                'error': '手牌は14枚である必要があります',
                'han': 0,
                'fu': 0,
                'cost': {'main': 0},
                'limit': 'なし',
                'yaku': [],
            }

        try:
            # タイル情報の変換
            tiles_136 = self._tiles_to_136_array(hand_tiles)
            # アガり牌は convert_tile_to_136 で正規化（英文字字牌にも対応）
            win_tile_136 = self.convert_tile_to_136(win_tile)

            # 変換に失敗した場合は invalid
            if not tiles_136 or win_tile_136 == 0:
                return {
                    'valid': False,
                    'error': 'タイル形式が無効です',
                    'han': 0,
                    'fu': 0,
                    'cost': {'main': 0},
                    'limit': 'なし',
                    'yaku': [],
                }
            
            # HandConfig を設定（player_wind/round_wind は HandConfig に渡す）
            config = HandConfig(is_tsumo=is_tsumo, player_wind=player_wind, round_wind=round_wind)
            config.is_dealer = is_dealer

            # ドラ表示牌を136形式に変換して渡す
            # ドラ表示牌のリストを136配列に変換（複数の牌に対応）
            dora_136 = []
            if dora_indicators:
                for ind in dora_indicators:
                    idx = self.convert_tile_to_136(ind)
                    if idx:
                        dora_136.append(idx)
            
            # Melds が指定されていない場合は空リストを使用
            if melds is None:
                melds = []

            # 手数を計算
            result = self.calculator.estimate_hand_value(
                tiles_136, win_tile_136, melds=melds, dora_indicators=dora_136, config=config
            )

            # 結果を整形
            # limit を翻数から判定
            limit = self._calculate_limit(result.han)
            
            return {
                'valid': result.error is None,
                'error': result.error,
                'han': result.han,
                'fu': result.fu,
                'cost': result.cost,  # 詳細な支払い情報をそのまま返す
                'limit': limit,
                'yaku': [yaku.name for yaku in result.yaku],
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'han': 0,
                'fu': 0,
                'cost': {'main': 0},
                'limit': 'なし',
                'yaku': [],
            }

    def _tiles_to_34_array(self, hand_tiles: List[str]) -> List[int]:
        """
        リスト形式の手牌を34配列に変換
        
        Args:
            hand_tiles: 手牌のリスト（例：['1m', '1m', '2p', ...]、字牌は'E'または'1z'形式）
        
        Returns:
            34要素の配列（各牌の枚数）
        """
        # 字牌マッピング: 数字表記 -> 英文字表記
        z_map = {'1z': 'E', '2z': 'S', '3z': 'W', '4z': 'N', '5z': 'P', '6z': 'F', '7z': 'C'}
        
        counts = [0] * 34
        for tile in hand_tiles:
            # 数字表記の字牌を英文字に変換
            tile_normalized = z_map.get(tile, tile)
            idx = TILE_INDEX.get(tile_normalized)
            if idx is not None:
                counts[idx] += 1
        return counts

    def _tiles_to_136_array(self, hand_tiles: List[str]) -> List[int]:
        """
        リスト形式の手牌を136配列に変換
        
        Args:
            hand_tiles: 手牌のリスト（例：['1m', '1m', '2p', ...]）
        
        Returns:
            136配列（各牌の詳細な位置情報）
        """
        # 手牌をマージしてタイル文字列に変換（one_line_string形式）
        tiles_str = self._hand_to_one_line_string(hand_tiles)
        
        if not tiles_str:
            return []
        
        try:
            return TilesConverter.one_line_string_to_136_array(tiles_str)
        except Exception:
            # フォーマット不正の場合は空リストを返す
            return []
    
    def convert_tile_to_136(self, tile: str) -> int:
        """
        単一の牌を136形式に変換（最初のコピーを返す）
        
        字牌は英文字表記または数字表記両方に対応します。
        mahjongライブラリの converter は英文字単独を受け付けないため
        数字表記 (1z-7z) に正規化してから変換します。
        
        Args:
            tile: 牌（例：'1m', 'E', 'P', '1z'）
        
        Returns:
            136形式のインデックス
        """
        # 英文字字牌を数字表記に変換
        z_map = {'E': '1z', 'S': '2z', 'W': '3z', 'N': '4z',
                 'P': '5z', 'F': '6z', 'C': '7z'}
        tile_norm = z_map.get(tile, tile)
        try:
            result = TilesConverter.one_line_string_to_136_array(tile_norm)
            return result[0] if result else 0
        except Exception:
            return 0

    def _calculate_limit(self, han: int) -> str:
        """
        翻数から限度（役の飾り）を計算
        
        Args:
            han: 翻数
        
        Returns:
            限度の名前（〇〇満、など）
        """
        if han >= 13:
            return '数え役満'
        elif han >= 11:
            return '三倍満'
        elif han >= 8:
            return '倍満'
        elif han >= 6:
            return '跳満'
        elif han >= 5:
            return '満貫'
        else:
            return 'なし'

    def _hand_to_one_line_string(self, hand_tiles: List[str]) -> str:
        """
        リスト形式の手牌をone_line_string形式に変換
        
        例: ['1m', '1m', '2p'] -> '11m2p' (one_line_string形式)
        字牌は両形式に対応：'E' または '1z'（東）
        mahjongライブラリの 136配列変換では数字表記が必要
        
        Args:
            hand_tiles: 手牌のリスト
        
        Returns:
            one_line_string形式の文字列（数字表記使用）
        """
        # 字牌マッピング: 英文字表記 -> 数字表記
        z_reverse_map = {'E': '1z', 'S': '2z', 'W': '3z', 'N': '4z', 'P': '5z', 'F': '6z', 'C': '7z'}
        # 字牌マッピング: 数字表記 -> 数字表記（そのまま）、英文字 -> 数字表記
        z_norm_map = {'1z': '1', '2z': '2', '3z': '3', '4z': '4', '5z': '5', '6z': '6', '7z': '7',
                      'E': '1', 'S': '2', 'W': '3', 'N': '4', 'P': '5', 'F': '6', 'C': '7'}
        
        # 手牌をソート＆グループ化
        suit_map = {'m': [], 'p': [], 's': [], 'z': []}
        
        # TILE_INDEX を使ったソート（両形式に対応）
        def tile_sort_key(t):
            # 数字表記を正規化してソートキーを取得
            if t in z_reverse_map:  # 英文字の場合
                t_norm = z_reverse_map[t]
            else:
                t_norm = t
            return TILE_INDEX.get(t_norm, TILE_INDEX.get(t, 999))
        
        for tile in sorted(hand_tiles, key=tile_sort_key):
            # 数字表記の1-9に正規化
            if tile in z_norm_map:
                # 字牌の場合
                suit_map['z'].append(z_norm_map[tile])
            elif len(tile) == 2:
                num, suit = tile[0], tile[1]
                if suit in suit_map:
                    suit_map[suit].append(num)
            elif len(tile) == 1:
                # 英文字の字牌（古い形式）
                if tile in z_norm_map:
                    suit_map['z'].append(z_norm_map[tile])
        
        # 形式化：数字と文字が交互
        result = []
        for suit in ['m', 'p', 's', 'z']:
            if suit_map[suit]:
                result.append(''.join(suit_map[suit]) + suit)
        
        return ''.join(result)

    def make_tenpai_with_next_win(self, hand_tiles: List[str]):
        """
        テスト用ユーティリティ。

        与えられた手牌（13枚想定）をほとんど影響を与えずに1枚だけ差し替えて
        『次に来る牌がアガリ牌になる（テンパイ状態）』となる手にする。

        戻す際に影響が少なくなるよう、差し替えたインデックスと元の牌を返す。

        Args:
            hand_tiles: 元の手牌のリスト（通常13枚）

        Returns:
            (new_hand, win_tile, revert_info) を返す。
            - new_hand: 変更後の手牌（13枚）
            - win_tile: その手牌に加えるとアガリになる牌文字列
            - revert_info: {'index': int, 'original': str, 'removed': Optional[str]}
              - index: 差し替えた位置
              - original: その位置に元々あった牌
              - removed: 入力が14枚で末尾から取り除いた牌があればその牌（None なら無し）

        注意: 入力手牌は変更しない（コピーを返す）。見つからない場合は (None, None, None) を返す。
        """
        # コピーして破壊的変更を避ける
        if not hand_tiles:
            return None, None, None

        hand = list(hand_tiles)
        removed = None
        # 14枚渡されている場合は末尾を一時的に取り除く（影響を小さくするため）
        if len(hand) == 14:
            removed = hand.pop()

        if len(hand) != 13:
            return None, None, None

        # 全ての牌種を試す（TILE_INDEX のキー）
        tile_types = list(TILE_INDEX.keys())

        for i in range(len(hand)):
            original = hand[i]
            for cand in tile_types:
                if cand == original:
                    continue
                tmp_hand = hand.copy()
                tmp_hand[i] = cand
                # その手にどの牌を足すとアガリになるか確認
                for win_cand in tile_types:
                    test_hand = tmp_hand + [win_cand]
                    if self.is_agari(test_hand):
                        revert_info = {'index': i, 'original': original, 'removed': removed}
                        return tmp_hand, win_cand, revert_info

        # 見つからなかった
        return None, None, None
