import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def test_get_agari_tiles_returns_waits_for_14_tile_debug_hand():
    game = Game(num_players=4, human_player_id=0)
    game.start_debug_tenpai_for_player0()

    waits = game.get_agari_tiles(0)

    assert waits
