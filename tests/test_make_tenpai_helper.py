import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.agari import AgariChecker


def test_make_tenpai_various_hands():
    checker = AgariChecker()

    samples = [
        # 13枚の手牌（比較的無害なサンプル）
        ['1m','2m','3m','4p','5p','6p','7s','8s','9s','E','E','1p','2p'],
        ['1m','1m','1m','2m','3m','4p','5p','6p','7s','8s','9s','E','E'],
        ['1m','1m','2m','2m','3m','3m','4p','4p','5p','5p','6s','6s','E'],
    ]

    for hand in samples:
        # 元手をコピーしておく
        original = list(hand)

        new_hand, win_tile, revert_info = checker.make_tenpai_with_next_win(hand)

        assert new_hand is not None and win_tile is not None and revert_info is not None

        # new_hand + [win_tile] はアガリになる
        assert checker.is_agari(new_hand + [win_tile])

        # revert_info に必要な情報が含まれる
        assert 'index' in revert_info and 'original' in revert_info and 'removed' in revert_info

        # 元に戻して一致すること（今回入力は13枚なので removed は None のはず）
        idx = revert_info['index']
        restored = list(new_hand)
        restored[idx] = revert_info['original']
        if revert_info['removed'] is not None:
            restored.append(revert_info['removed'])

        assert restored == original
