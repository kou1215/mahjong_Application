import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.game import Game


def test_is_furiten_true_when_wait_in_own_discards():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    # 1p待ちのテンパイ形（111m 234m 567m 789m 11p）
    game.players[1].hand.tiles = ['1m', '1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '1p']
    game.players[1].discards = ['1p']

    assert game.is_furiten(1) is True


def test_furiten_blocks_ron_in_check_available_calls():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.players[1].hand.tiles = ['1m', '1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '1p']
    game.players[1].discards = ['1p']

    calls = game.check_available_calls(1, '1p')
    assert calls['can_ron'] is False


def test_furiten_blocks_ron_in_build_call_options():
    game = Game(num_players=4, human_player_id=0)
    game.start_game()

    game.players[1].hand.tiles = ['1m', '1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '1p']
    game.players[1].discards = ['1p']

    options = game._build_call_options(discarder_id=0, discarded_tile='1p')
    entry = next(item for item in options if item['player_id'] == 1)
    assert entry['calls']['can_ron'] is False
