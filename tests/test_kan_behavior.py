import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def test_open_kan_increases_dora_indicator():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    initial_dora = game.dora_indicator
    game.last_discarded = '5m'
    game.players[1].hand.tiles = ['5m', '5m', '5m', '1p', '2p', '3p', '4p', '6p', '7p', '8p', '1s', '2s', '3s']

    ok = game.apply_kan(player_id=1, tile='5m', is_closed=False)

    assert ok is True
    assert game.kan_count == 1
    if len(game.dead_wall) >= 7:
        assert game.dora_indicator == game.dead_wall[6]
    else:
        assert game.dora_indicator == initial_dora


def test_get_agari_tiles_works_with_kan_meld_as_three_tiles():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    # Player0: 1111m を副露カンとして保持し、暗部11枚をテンパイ形にする
    game.players[0].melds = [['1m', '1m', '1m', '1m']]
    game.players[0].hand.tiles = ['2p', '3p', '4p', '2s', '3s', '4s', '6s', '7s', '8s', '5p', '5p']

    waits = game.get_agari_tiles(0)

    assert waits
    assert '5p' in waits


def test_cannot_declare_riichi_after_kan_meld():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.current_turn = 0
    game.last_discarded = '5m'
    game.players[0].hand.tiles = ['5m', '5m', '5m', '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '1s', '2s']

    ok = game.apply_kan(player_id=0, tile='5m', is_closed=False)
    assert ok is True
    assert game.players[0].melds

    result = game.process_discard(discard_index=0, declare_riichi=True)

    assert result.get('error') == 'Cannot declare riichi after calling melds'
    assert game.players[0].is_riichi is False
