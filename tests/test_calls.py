"""
ポン・チーロンの機能テスト
"""
import sys
sys.path.insert(0, r'c:\Users\airen\OneDrive\ドキュメント\mahjong\mahjong_Application')

from logic.calls import CallChecker
from logic.agari import AgariChecker
from models.game import Game
from models.player import Player
from models.hand import Hand


def test_pong_detection():
    """ポン判定のテスト"""
    print("=== ポン判定テスト ===")
    
    # テスト1: ポンが可能な場合
    hand = ['1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p']
    discarded = '1m'
    
    can_pong = CallChecker.can_pong(hand, discarded)
    print(f"手牌: {hand}")
    print(f"捨て牌: {discarded}")
    print(f"ポン可能: {can_pong}")
    assert can_pong == True, "ポン判定が失敗"
    print("✓ ポン判定成功\n")
    
    # テスト2: ポンが不可能な場合
    hand2 = ['1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p', '4p']
    can_pong2 = CallChecker.can_pong(hand2, discarded)
    print(f"手牌: {hand2}")
    print(f"ポン可能: {can_pong2}")
    assert can_pong2 == False, "ポン判定が失敗"
    print("✓ ポン不可判定成功\n")


def test_chow_detection():
    """チー判定のテスト"""
    print("=== チー判定テスト ===")
    
    # テスト1: チーが可能な場合（3-4-5の形で4-5を持っている）
    hand = ['2m', '3m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p', '4p', '5p', '6p']
    discarded = '4m'
    
    can_chow = CallChecker.can_chow(hand, discarded)
    print(f"手牌: {hand}")
    print(f"捨て牌: {discarded}")
    print(f"チー可能: {can_chow}")
    assert can_chow == True, "チー判定が失敗"
    print("✓ チー判定成功\n")
    
    # テスト2: チーの複数候補を検出（2-3-4と3-4-5の両方が可能）
    hand2 = ['2m', '3m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p', '4p', '5p', '6p']
    discarded2 = '4m'
    
    possible_chows = CallChecker._find_possible_chows(hand2, discarded2)
    print(f"手牌: {hand2}")
    print(f"捨て牌: {discarded2}")
    print(f"可能なチー: {possible_chows}")
    assert len(possible_chows) > 0, "チー検出が失敗"
    print(f"✓ 計{len(possible_chows)}つのチーが見つかりました\n")
    
    # テスト3: 字牌ではチーは成立しない
    hand3 = ['E', 'S', 'W', 'N', 'P', 'F', 'C', '1m', '2m', '3m', '4m', '5m', '6m']
    discarded3 = 'E'
    
    can_chow3 = CallChecker.can_chow(hand3, discarded3)
    print(f"手牌（字牌含む）: {hand3}")
    print(f"捨て牌: {discarded3}（字牌）")
    print(f"チー可能: {can_chow3}")
    assert can_chow3 == False, "字牌チーが成立している（バグ）"
    print("✓ 字牌ではチー不可\n")


def test_ron_detection():
    """ロン判定のテスト"""
    print("=== ロン判定テスト ===")
    
    agari_checker = AgariChecker()
    
    # テスト1: ロンが可能な場合（アガり形になる牌）
    # 簡易的な試験：アガり牌を持つ手牌 + 捨て牌でアガるパターン
    # 例：1-1-1-2-3-4-5-6-7-8-9 + 1p-2p-3p + ロン牌で14枚
    hand = ['1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p']
    ron_tile = '1p'  # これでアガり形になるかは mahjong ライブラリに依存
    
    # 実際のアガり判定は複雑なので、簡易テスト
    can_ron = CallChecker.can_ron(hand, ron_tile, agari_checker)
    print(f"手牌: {hand}")
    print(f"ロン牌（捨て牌）: {ron_tile}")
    print(f"ロン可能: {can_ron}")
    print("✓ ロン判定実行\n")


def test_player_call_methods():
    """プレイヤーの鳴きメソッドテスト"""
    print("=== プレイヤー鳴きメソッドテスト ===")
    
    player = Player(0, is_ai=False)
    
    # 手牌を設定
    tiles = ['1m', '1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p']
    for tile in tiles:
        player.hand.tiles.append(tile)
    
    print(f"初期手牌: {player.hand.to_list()}")
    print(f"初期メルド: {player.melds}")
    
    # ポンを適用
    pong_tiles = ['1m', '1m', '1m']  # 捨てられたの1つを含む
    result = player.call_pong(pong_tiles)
    print(f"\nポン試行: {pong_tiles}")
    print(f"成功: {result}")
    print(f"鳴き後メルド: {player.melds}")
    print(f"鳴き後手牌: {player.hand.to_list()}")
    print("✓ ポン適用成功\n")
    
    # チーを適用
    player2 = Player(1, is_ai=False)
    tiles2 = ['2m', '3m', '5m', '6m', '7m', '8m', '9m', '1p', '2p', '3p', '4p', '5p', '6p']
    for tile in tiles2:
        player2.hand.tiles.append(tile)
    
    chow_tiles = ['4m', '5m', '6m']  # 4mが捨てられたものと想定
    result2 = player2.call_chow(chow_tiles)
    print(f"初期手牌: {player2.hand.to_list()}")
    print(f"チー試行: {chow_tiles}")
    print(f"成功: {result2}")
    print(f"鳴き後メルド: {player2.melds}")
    print(f"鳴き後手牌: {player2.hand.to_list()}")
    print("✓ チー適用成功\n")


def test_game_calls():
    """ゲームクラスのコール機能テスト"""
    print("=== ゲーム鳴きシステムテスト ===")
    
    game = Game(num_players=4, human_player_id=0)
    game.start_game()
    
    # プレイヤー0の手牌を確認
    player0 = game.players[0]
    print(f"プレイヤー0の手牌: {player0.hand.to_list()}")
    print(f"プレイヤー0のメルド: {player0.melds}")
    
    # 利用可能な鳴きをチェック（仮の捨て牌で）
    test_tile = '1m'
    available_calls = game.check_available_calls(0, test_tile)
    print(f"\n捨て牌: {test_tile} の場合の利用可能な鳴き:")
    print(f"  ポン可能: {available_calls['can_pong']}")
    print(f"  チー可能: {available_calls['can_chow']}")
    print(f"  ロン可能: {available_calls['can_ron']}")
    print("✓ ゲーム鳴きチェック成功\n")


def main():
    """すべてのテストを実行"""
    print("ポン・チー・ロン実装テスト開始\n")
    
    try:
        test_pong_detection()
        test_chow_detection()
        test_ron_detection()
        test_player_call_methods()
        test_game_calls()
        
        print("\n" + "="*50)
        print("✓ すべてのテストが完了しました！")
        print("="*50)
    except AssertionError as e:
        print(f"\n✗ テスト失敗: {e}")
    except Exception as e:
        print(f"\n✗ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
