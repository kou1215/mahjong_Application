import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def _mock_value(*args, **kwargs):
    return {
        'valid': True,
        'han': 3,
        'fu': 30,
        'cost': {'main': 3900, 'total': 3900},
        'limit': 'なし',
        'yaku': ['立直'],
    }


def test_ron_resolves_immediately_ignoring_other_pending_choices():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()
    game.estimate_agari_value = _mock_value  # type: ignore[assignment]

    game.phase = 'call_wait'
    game.last_discarded = '1m'
    game.pending_calls = [
        {'player_id': 1, 'calls': {'can_ron': True, 'can_pong': False, 'can_kan': False, 'can_chow': False}, 'chow_combos': []},
        {'player_id': 2, 'calls': {'can_ron': False, 'can_pong': True, 'can_kan': False, 'can_chow': False}, 'chow_combos': []},
    ]

    result = game.resolve_pending_call(player_id=1, action='ron', tiles=['1m'])

    assert result['ok'] is True
    assert result['action'] == 'ron'
    assert result['agari'] is True


def test_pong_resolves_immediately_when_no_ron_candidate_remains():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.phase = 'call_wait'
    game.last_discarded = '3m'
    game.pending_calls = [
        {'player_id': 1, 'calls': {'can_ron': False, 'can_pong': True, 'can_kan': False, 'can_chow': False}, 'chow_combos': []},
        {'player_id': 2, 'calls': {'can_ron': False, 'can_pong': False, 'can_kan': False, 'can_chow': True}, 'chow_combos': [['1m', '2m', '3m']]},
    ]

    # ポン成立できるように手牌を調整
    game.players[1].hand.tiles = ['3m', '3m', '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p', '1s', '2s']

    result = game.resolve_pending_call(player_id=1, action='pong', tiles=[])

    assert result['ok'] is True
    assert result['action'] == 'pong'
    assert game.current_turn == 1


def test_pong_waits_if_unresolved_ron_candidate_exists():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.phase = 'call_wait'
    game.last_discarded = '5p'
    game.pending_calls = [
        {'player_id': 1, 'calls': {'can_ron': False, 'can_pong': True, 'can_kan': False, 'can_chow': False}, 'chow_combos': []},
        {'player_id': 2, 'calls': {'can_ron': True, 'can_pong': False, 'can_kan': False, 'can_chow': False}, 'chow_combos': []},
    ]

    game.players[1].hand.tiles = ['5p', '5p', '1m', '2m', '3m', '4m', '6m', '7m', '8m', '9m', '1s', '2s', '3s']

    result = game.resolve_pending_call(player_id=1, action='pong', tiles=[])

    assert result['ok'] is True
    assert result['action'] == 'waiting'
    assert result['awaiting_call'] is True
