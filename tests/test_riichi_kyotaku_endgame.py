import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def _value_ron_3900(*args, **kwargs):
    return {
        'valid': True,
        'han': 2,
        'fu': 30,
        'cost': {'main': 3900, 'total': 3900},
        'limit': 'なし',
        'yaku': ['立直'],
    }


def test_riichi_deposit_consumes_1000_and_adds_kyotaku():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.players[0].points = 25000
    ok = game._apply_riichi_deposit(0)

    assert ok is True
    assert game.players[0].points == 24000
    assert game.kyotaku_riichi == 1


def test_kyotaku_is_paid_to_winner_on_ron():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    for p in game.players:
        p.points = 25000

    game.kyotaku_riichi = 2
    winner_id = 1
    discarder_id = 0
    game.current_discarder_id = discarder_id
    game.last_discarded = '3m'
    game.received_calls = {str(winner_id): {'action': 'ron', 'tiles': ['3m']}}
    game.estimate_agari_value = _value_ron_3900  # type: ignore[assignment]

    result = game._execute_highest_priority_call()

    assert result['action'] == 'ron'
    assert game.players[winner_id].points == 30900
    assert game.players[discarder_id].points == 21100
    assert game.kyotaku_riichi == 0
    assert {'from': -1, 'to': winner_id, 'amount': 2000} in result['point_movements']


def test_end_game_when_configured_conditions_are_satisfied():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.set_end_game_conditions(
        require_all_dealers_experienced=True,
        require_all_non_negative_points=True,
        ignore_dealer_win_for_end=True,
    )
    game.dealer_experience = [True, True, True, True]
    game.dealer_id = 0

    for p in game.players:
        p.points = 25000

    winner_id = 1  # 非親
    game.check_agari = lambda player_id: True  # type: ignore[assignment]
    game.estimate_agari_value = _value_ron_3900  # type: ignore[assignment]
    game.current_discarder_id = 0

    result = game.check_and_calculate_win(player_id=winner_id, win_tile='1m', is_tsumo=False)

    assert result['agari'] is True
    assert result.get('new_hand_started') is None
    assert result['is_game_over'] is True
    assert game.is_game_over is True
    assert result['final_settlement'] is not None
    assert 'ranking' in result['final_settlement']


def test_dealer_win_does_not_end_game_under_current_rule():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.set_end_game_conditions(
        require_all_dealers_experienced=True,
        require_all_non_negative_points=True,
        ignore_dealer_win_for_end=True,
    )
    game.dealer_experience = [True, True, True, True]
    game.dealer_id = 0

    for p in game.players:
        p.points = 25000

    winner_id = 0  # 親
    game.check_agari = lambda player_id: True  # type: ignore[assignment]
    game.estimate_agari_value = _value_ron_3900  # type: ignore[assignment]
    game.current_discarder_id = 1

    result = game.check_and_calculate_win(player_id=winner_id, win_tile='1m', is_tsumo=False)

    assert result['agari'] is True
    assert result.get('new_hand_started') is True
    assert result.get('is_game_over', False) is False
    assert game.is_game_over is False


def test_game_ends_if_any_player_drops_below_zero_after_agari():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.set_end_game_conditions(
        require_all_dealers_experienced=True,
        require_all_non_negative_points=True,
        end_on_negative_points=True,
        ignore_dealer_win_for_end=True,
    )
    game.dealer_experience = [False, False, False, False]
    game.dealer_id = 0

    for p in game.players:
        p.points = 25000
    game.players[2].points = 3000

    winner_id = 1
    game.check_agari = lambda player_id: True  # type: ignore[assignment]
    game.estimate_agari_value = _value_ron_3900  # type: ignore[assignment]
    game.current_discarder_id = 2

    result = game.check_and_calculate_win(player_id=winner_id, win_tile='1m', is_tsumo=False)

    assert result['agari'] is True
    assert game.players[2].points == -900
    assert result.get('is_game_over') is True
    assert game.is_game_over is True
    assert result.get('final_settlement') is not None
