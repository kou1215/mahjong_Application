import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.agari import AgariChecker
from mahjong.constants import EAST, SOUTH, WEST, NORTH

checker = AgariChecker()

# 手牌：1m2m3m, 4p5p6p, 7s8s9s, 東東東(役牌), 1p1p (対子)
hand = ['1m','2m','3m','4p','5p','6p','7s','8s','9s','E','E','E','1p','1p']
win = '1p'

cases = [
    ('seat East, round South, no dora', EAST, SOUTH, None),
    ('seat South, round East, no dora', SOUTH, EAST, None),
    ('seat East, round South, dora 1m', EAST, SOUTH, ['1m']),
    # white indicator should make green dragon a dora
    ('seat East, round South, dora white (P)', EAST, SOUTH, ['P']),
]

for desc, player_wind, round_wind, dora_ind in cases:
    # use a different hand when testing white-indicator case (need green dragons)
    if desc.endswith('white (P)'):
        test_hand = ['1m','2m','3m','4p','5p','6p','7s','8s','9s','E','E','F','F','F']
        win_tile = 'F'
    else:
        test_hand = hand
        win_tile = win

    # convert dora indicators to 136-form for debugging
    dora_136 = []
    if dora_ind:
        for ind in dora_ind:
            d_idx = checker.convert_tile_to_136(ind)
            dora_136.append(d_idx)
    print('converted dora indicators (136):', dora_136)
    # show tiles in 136 and count dora with mahjong.utils.plus_dora for debugging
    from mahjong.tile import TilesConverter
    from mahjong.utils import plus_dora
    tiles_136 = checker._tiles_to_136_array(test_hand)
    print('tiles_136 sample (first 10):', tiles_136[:10])
    if dora_136:
        count = sum(plus_dora(t, dora_136) for t in tiles_136)
        print('manual plus_dora count:', count)

    res = checker.estimate_hand_value(
        test_hand, win_tile, is_tsumo=False, is_dealer=False, melds=None,
        player_wind=player_wind, round_wind=round_wind, dora_indicators=dora_ind
    )
    print('CASE:', desc)
    print(res)
    print('\n')
