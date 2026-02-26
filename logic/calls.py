"""
ポン・チー・ロンなどの鳴き判定と処理
"""
from typing import List, Dict, Optional, Tuple
from mahjong.meld import Meld


class CallChecker:
    """ポン・チー・ロン判定クラス"""

    @staticmethod
    def can_pong(hand_tiles: List[str], discarded_tile: str) -> bool:
        """
        ポン（同じ牌3つ）が可能かどうか判定
        
        Args:
            hand_tiles: 自プレイヤーの手牌
            discarded_tile: 捨てられた牌
        
        Returns:
            ポンが可能なら True
        """
        # 捨てられた牌と同じものが手牌に2枚以上あるかチェック
        count = hand_tiles.count(discarded_tile)
        return count >= 2

    @staticmethod
    def can_chow(hand_tiles: List[str], discarded_tile: str) -> bool:
        """
        チー（1つの連続牌を作る）が可能かどうか判定
        
        チーは捨てられた牌が3連続の「第1牌」「第2牌」「第3牌」のいずれかになる場合に成立
        例：3mが捨てられたら、3-4-5 または 2-3-4 の形でチーが成立
        
        Args:
            hand_tiles: 自プレイヤーの手牌
            discarded_tile: 捨てられた牌
        
        Returns:
            チーが可能なら True（複数形の場合を考慮して True/False のみ）
        """
        # チーの可能な形を検出するヘルパー関数
        possible_chows = CallChecker._find_possible_chows(hand_tiles, discarded_tile)
        return len(possible_chows) > 0

    @staticmethod
    def _find_possible_chows(hand_tiles: List[str], discarded_tile: str) -> List[Tuple[str, str, str]]:
        """
        チーの可能な組み合わせをすべて検出
        
        Args:
            hand_tiles: 自プレイヤーの手牌
            discarded_tile: 捨てられた牌
        
        Returns:
            可能なチーの組み合わせリスト（例：[('2m', '3m', '4m'), ...]）
        """
        possible_chows = []

        # 数牌かどうか確認（字牌ではチーは成立しない）
        if not CallChecker._is_number_tile(discarded_tile):
            return []

        # 捨てられた牌のスート（万・筒・索）と数字を取得
        suit = discarded_tile[-1]
        num_str = discarded_tile[:-1]
        
        try:
            num = int(num_str)
        except ValueError:
            return []

        # 数字が1-9の範囲内かチェック
        if num < 1 or num > 9:
            return []

        # チーの3つの可能なパターン：
        # パターン1：捨てられた牌が第1牌 (n, n+1, n+2)
        # パターン2：捨てられた牌が第2牌 (n-1, n, n+1)
        # パターン3：捨てられた牌が第3牌 (n-2, n-1, n)

        patterns = []
        if num <= 7:  # パターン1
            patterns.append((num, num + 1, num + 2))
        if 2 <= num <= 8:  # パターン2
            patterns.append((num - 1, num, num + 1))
        if num >= 3:  # パターン3
            patterns.append((num - 2, num - 1, num))

        # 各パターンに対して手牌にあるかチェック
        for pattern in patterns:
            tiles_needed = [f"{n}{suit}" for n in pattern]
            # ⅰ.捨てられた牌を除いた、必要な牌を特定
            other_tiles = [t for t in tiles_needed if t != discarded_tile]

            # ii. 手牌に必要な牌がすべてあるかチェック
            if all(t in hand_tiles for t in other_tiles):
                possible_chows.append(tuple(tiles_needed))

        return possible_chows

    @staticmethod
    def can_ron(hand_tiles: List[str], discarded_tile: str, agari_checker) -> bool:
        """
        ロン（他プレイヤーの捨て牌で和了）が可能かどうか判定
        
        Args:
            hand_tiles: 自プレイヤーの手牌（14枚=13+ツモ牌）
            discarded_tile: 捨てられた牌
            agari_checker: AgariCheckのインスタンス
        
        Returns:
            ロンが可能なら True
        """
        # ロン用の仮の手牌を作成（捨てられた牌を追加）
        ron_hand = hand_tiles + [discarded_tile]
        
        # 14枚に調整（13+1）
        if len(ron_hand) != 14:
            return False

        # ロン用の判定（ツモではなくロンなので is_tsumo=False）
        return agari_checker.is_agari(ron_hand)

    @staticmethod
    def can_kan(hand_tiles: List[str], discarded_tile: str) -> bool:
        """
        カン（捨て牌で明槓）が可能かどうか判定（手持ちに同じ牌が3枚あるか）

        Args:
            hand_tiles: 自プレイヤーの手牌
            discarded_tile: 捨てられた牌

        Returns:
            カンが可能なら True
        """
        count = hand_tiles.count(discarded_tile)
        return count >= 3

    @staticmethod
    def _is_number_tile(tile: str) -> bool:
        """
        数牌（万・筒・索）かどうか判定（字牌は False）
        
        Args:
            tile: 牌（例：'1m', '5p', '3s'）
        
        Returns:
            数牌なら True
        """
        if len(tile) < 2:
            return False
        suit = tile[-1]
        return suit in ['m', 'p', 's']

    @staticmethod
    def create_meld(tiles: Tuple[str, str, str], meld_type: str) -> Optional[Meld]:
        """
        鳴きのMeldオブジェクトを作成
        
        Args:
            tiles: 牌の3つ組 (例：('2m', '3m', '4m'))
            meld_type: 鳴きのタイプ ('pung'=ポン, 'chow'=チー）
        
        Returns:
            Meldオブジェクト
        """
        # tiles -> 136形式に変換（簡易版）
        # 実装は必要に応じて拡張
        if meld_type == 'pung':
            # ポンの場合、3つとも同じ牌
            pass
        elif meld_type == 'chow':
            # チーの場合、連続する3牌
            pass
        
        return None


class CallAction:
    """鳴きアクション（ユーザーの選択）"""

    def __init__(self, player_id: int, action_type: str, tiles: List[str] = None):
        """
        Args:
            player_id: プレイヤーID
            action_type: アクションタイプ ('pong', 'chow', 'ron', 'pass')
            tiles: 使用する牌のリスト（ポン・チーの場合）
        """
        self.player_id = player_id
        self.action_type = action_type  # 'pong', 'chow', 'ron', 'pass'
        self.tiles = tiles or []

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'player_id': self.player_id,
            'action_type': self.action_type,
            'tiles': self.tiles,
        }

    def __repr__(self) -> str:
        return f"CallAction({self.player_id}, {self.action_type}, {self.tiles})"
