import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.agari import AgariChecker


def test_honba_adds_300_per_hand_on_ron():
    checker = AgariChecker()
    hand_tiles = ['E', 'E', 'E', '2m', '3m', '4m', '2p', '3p', '4p', '2s', '3s', '4s', '5s']

    base = checker.estimate_hand_value(
        hand_tiles=hand_tiles,
        win_tile='5s',
        is_tsumo=False,
        honba_count=0,
    )
    with_honba = checker.estimate_hand_value(
        hand_tiles=hand_tiles,
        win_tile='5s',
        is_tsumo=False,
        honba_count=2,
    )

    assert base['valid'] is True
    assert with_honba['valid'] is True
    assert with_honba['cost']['total'] - base['cost']['total'] == 600


def test_honba_adds_100_per_opponent_on_tsumo():
    checker = AgariChecker()
    hand_tiles = ['E', 'E', 'E', '2m', '3m', '4m', '2p', '3p', '4p', '2s', '3s', '4s', '5s']

    base = checker.estimate_hand_value(
        hand_tiles=hand_tiles,
        win_tile='5s',
        is_tsumo=True,
        honba_count=0,
    )
    with_honba = checker.estimate_hand_value(
        hand_tiles=hand_tiles,
        win_tile='5s',
        is_tsumo=True,
        honba_count=2,
    )

    assert base['valid'] is True
    assert with_honba['valid'] is True
    assert with_honba['cost']['main_bonus'] - base['cost']['main_bonus'] == 200
    assert with_honba['cost']['additional_bonus'] - base['cost']['additional_bonus'] == 200
    assert with_honba['cost']['total'] - base['cost']['total'] == 600
