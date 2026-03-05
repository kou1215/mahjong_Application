import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.agari import AgariChecker


def test_open_tanyao_is_valid_with_open_rule_enabled():
    checker = AgariChecker()

    # 副露: 4m5m6m（チー）
    # 手牌（暗部）: 234p 345s 678s 66p
    # すべて么九牌なし -> タンヤオ成立
    res = checker.estimate_hand_value(
        hand_tiles=['2p', '3p', '4p', '6s', '7s', '8s', '3s', '4s', '5s', '6p', '6p'],
        win_tile='4p',
        is_tsumo=True,
        melds=[['4m', '5m', '6m']],
    )

    assert res['valid'] is True
    assert '断么九' in res['yaku']
