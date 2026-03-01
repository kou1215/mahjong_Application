import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mahjong.constants import EAST, SOUTH
from models.game import Game


def _always_valid_value(*args, **kwargs):
    return {
        'valid': True,
        'han': 3,
        'fu': 30,
        'cost': {'main': 3900, 'total': 3900},
        'limit': 'なし',
        'yaku': ['Riichi'],
    }


def test_dealer_agari_increases_honba_and_keeps_dealer():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.dealer_id = 0
    game.honba = 0
    game.check_agari = lambda player_id: True  # type: ignore[assignment]
    game.estimate_agari_value = _always_valid_value  # type: ignore[assignment]

    result = game.check_and_calculate_win(player_id=0, win_tile='1m', is_tsumo=True, is_riichi=False)

    assert result['agari'] is True
    assert game.dealer_id == 0
    assert game.honba == 1


def test_non_dealer_ron_moves_dealer_and_resets_honba():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.dealer_id = 0
    game.honba = 2
    winner_id = 1
    game.players[winner_id].is_riichi = True
    game.last_discarded = '1m'
    game.received_calls = {str(winner_id): {'action': 'ron', 'tiles': ['1m']}}
    game.estimate_agari_value = _always_valid_value  # type: ignore[assignment]

    result = game._execute_highest_priority_call()

    assert result['ok'] is True
    assert result['action'] == 'ron'
    assert game.dealer_id == 1
    assert game.honba == 0

    seat_winds = game.get_seat_winds()
    assert seat_winds[1] == EAST
    assert seat_winds[2] == SOUTH


def test_round_wind_advances_when_dealer_wraps():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.round_wind = EAST
    game.dealer_id = 3
    game.honba = 1

    winner_id = 0
    game.players[winner_id].is_riichi = False
    game.last_discarded = '1m'
    game.received_calls = {str(winner_id): {'action': 'ron', 'tiles': ['1m']}}
    game.estimate_agari_value = _always_valid_value  # type: ignore[assignment]

    result = game._execute_highest_priority_call()

    assert result['ok'] is True
    assert result['action'] == 'ron'
    assert game.dealer_id == 0
    assert game.round_wind == SOUTH
