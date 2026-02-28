import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.agari import AgariChecker
from models.game import Game


def test_ippatsu_scoring_enabled_only_when_flag_true():
    checker = AgariChecker()
    hand = ['2m', '3m', '4m', '4m', '5m', '6m', '2p', '3p', '4p', '3s', '4s', '5s', '6s', '6s']
    win_tile = '6s'

    no_ippatsu = checker.estimate_hand_value(
        hand_tiles=hand,
        win_tile=win_tile,
        is_tsumo=False,
        is_riichi=True,
        is_ippatsu=False,
    )
    with_ippatsu = checker.estimate_hand_value(
        hand_tiles=hand,
        win_tile=win_tile,
        is_tsumo=False,
        is_riichi=True,
        is_ippatsu=True,
    )

    assert no_ippatsu['valid']
    assert with_ippatsu['valid']
    assert with_ippatsu['han'] == no_ippatsu['han'] + 1
    assert any('ippatsu' in y.lower() for y in with_ippatsu['yaku'])


def test_ippatsu_is_cleared_when_call_happens():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.ippatsu_eligible = [True, False, False, False]
    game.last_discarded = '1m'
    game.players[1].hand.tiles = ['1m', '1m', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p', '1s', '2s', '3s']

    ok = game.apply_pong(1, ['1m', '1m', '1m'])

    assert ok
    assert game.ippatsu_eligible == [False, False, False, False]


def test_riichi_auto_discard_uses_drawn_tile_and_locked_waits():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    # Player 0 の手番でリーチ宣言打牌（13枚固定後の待ちを保持）
    game.current_turn = 0
    game.players[0].hand.tiles = ['1m','2m','3m','2p','3p','4p','3s','4s','5s','6s','6s','7s','8s','9s']
    result = game.process_discard(discard_index=13, declare_riichi=True)
    assert game.players[0].is_riichi
    assert game.riichi_locked_hands[0] is not None
    assert game.riichi_wait_tiles[0]

    # 次巡で非和了牌をツモらせる（自動ツモ切りで同牌が捨てられること）
    base_hand = list(game.riichi_locked_hands[0])
    game.current_turn = 0
    game.phase = 'discard'
    game.pending_calls = []
    game.last_discarded = None
    game.players[0].hand.tiles = list(base_hand)

    non_win = next(t for t in ['1m','5m','9m','1p','9p','1s','9s','E'] if t not in game.riichi_wait_tiles[0])
    game.players[0].add_tile(non_win)
    auto_result = game._auto_discard_after_riichi_if_needed(non_win)
    assert auto_result['auto_log']
    assert auto_result['auto_log'][0]['player'] == 0
    assert auto_result['auto_log'][0]['discarded'] == non_win
    assert sorted(game.players[0].hand.to_list()) == sorted(base_hand)

    # 和了牌をツモった場合は自動打牌しない
    win_tile = game.riichi_wait_tiles[0][0]
    game.current_turn = 0
    game.phase = 'discard'
    game.pending_calls = []
    game.last_discarded = None
    game.players[0].hand.tiles = list(base_hand)
    game.players[0].add_tile(win_tile)
    win_auto_result = game._auto_discard_after_riichi_if_needed(win_tile)
    assert win_auto_result['auto_log'] == []
    assert game.players[0].hand.to_list().count(win_tile) >= 1


def test_riichi_player_can_only_ron_or_pass():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.players[1].is_riichi = True
    game.players[1].hand.tiles = ['1m', '1m', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p', '1s', '2s', '3s']
    game.last_discarded = '1m'

    calls = game.check_available_calls(1, '1m')
    assert calls['can_pong'] is False
    assert calls['can_chow'] is False

    assert game.apply_pong(1, ['1m', '1m', '1m']) is False
    assert game.apply_chow(1, ['1m', '2m', '3m']) is False
    assert game.apply_kan(1, '1m', is_closed=False) is False

    game.phase = 'call_wait'
    game.pending_calls = [{'player_id': 1, 'calls': {'can_ron': True, 'can_pong': False, 'can_chow': False, 'can_kan': False}, 'chow_combos': []}]
    result = game.resolve_pending_call(player_id=1, action='pong', tiles=[])
    assert result['ok'] is False
    assert 'ron or pass' in result['error']


def test_ron_response_includes_ura_dora_indicator_for_riichi():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    winner_id = 1
    game.players[winner_id].is_riichi = True
    game.last_discarded = '1m'
    game.received_calls = {str(winner_id): {'action': 'ron', 'tiles': ['1m']}}

    # 点数計算に成功するよう簡易モック
    def mock_estimate(*args, **kwargs):
        return {'valid': True, 'han': 3, 'fu': 30, 'cost': {'main': 3900, 'total': 3900}, 'limit': 'なし', 'yaku': ['Riichi']}

    game.estimate_agari_value = mock_estimate  # type: ignore[assignment]

    result = game._execute_highest_priority_call()
    assert result['ok'] is True
    assert result['action'] == 'ron'
    assert 'ura_dora_indicator' in result
    assert result['ura_dora_indicator'] == game.dead_wall[5]
