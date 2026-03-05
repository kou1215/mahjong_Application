import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def test_ron_transfers_points_from_discarder_to_winner():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    for p in game.players:
        p.points = 25000

    winner_id = 1
    discarder_id = 2
    game.current_discarder_id = discarder_id
    game.last_discarded = '5m'
    game.received_calls = {str(winner_id): {'action': 'ron', 'tiles': ['5m']}}

    game.estimate_agari_value = lambda *args, **kwargs: {
        'valid': True,
        'han': 3,
        'fu': 40,
        'cost': {'main': 7700, 'total': 7700},
        'limit': 'なし',
        'yaku': ['立直'],
    }  # type: ignore[assignment]

    result = game._execute_highest_priority_call()

    assert result['action'] == 'ron'
    assert game.players[winner_id].points == 32700
    assert game.players[discarder_id].points == 17300
    assert game.players[0].points == 25000
    assert game.players[3].points == 25000
    assert result['point_movements'] == [{'from': discarder_id, 'to': winner_id, 'amount': 7700}]


def test_tsumo_transfers_points_from_all_opponents():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    for p in game.players:
        p.points = 25000

    game.dealer_id = 0
    winner_id = 1  # 子

    game.check_agari = lambda player_id: True  # type: ignore[assignment]
    game.estimate_agari_value = lambda *args, **kwargs: {
        'valid': True,
        'han': 5,
        'fu': 30,
        'cost': {'main': 4000, 'additional': 2000, 'total': 8000},
        'limit': '満貫',
        'yaku': ['門前清自摸和'],
    }  # type: ignore[assignment]

    result = game.check_and_calculate_win(player_id=winner_id, win_tile='1m', is_tsumo=True)

    assert result['agari'] is True
    assert game.players[winner_id].points == 33000
    assert game.players[0].points == 21000  # 親払い
    assert game.players[2].points == 23000
    assert game.players[3].points == 23000

    assert {'from': 0, 'to': winner_id, 'amount': 4000} in result['point_movements']
    assert {'from': 2, 'to': winner_id, 'amount': 2000} in result['point_movements']
    assert {'from': 3, 'to': winner_id, 'amount': 2000} in result['point_movements']
