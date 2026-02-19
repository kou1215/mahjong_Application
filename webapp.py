
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import mahjong_app

app = Flask(__name__)
# セッション用のシークレットキー（本番ではより安全な値に）
app.secret_key = 'your_secret_key_here'

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    turns = 8
    hands_view = None

    # リセット要求があればセッションをクリア
    if request.args.get('reset'):
        session.clear()
    # セッションからwallとhandsを取得
    wall = session.get('wall')
    hands = session.get('hands')

    # セッションデータの整合性チェック
    valid = True
    if not isinstance(wall, list) or not isinstance(hands, list) or len(hands) != 4:
        valid = False
    else:
        for h in hands:
            if not isinstance(h, list):
                valid = False
                break
    if not valid:
        session.clear()
        wall = None
        hands = None

    if wall is None or hands is None:
        # 新規対局
        try:
            turns = int(request.form.get('turns', 8))
        except (ValueError, TypeError):
            turns = 8
        wall = mahjong_app.build_wall()
        hands = mahjong_app.deal(wall)
        # 新規配牌直後に必ずソート
        hands = [mahjong_app.sort_hand(h) for h in hands]
        session['wall'] = wall.copy()
        session['hands'] = [h.copy() for h in hands]
    else:
        # セッションから復元（既存データを維持）
        try:
            turns = int(request.form.get('turns', 8))
        except (ValueError, TypeError):
            turns = 8
        hands = [h.copy() for h in session['hands']]
        wall = session['wall'].copy() if session.get('wall') else None

    # hands_viewの作成

    hands_view = []
    for i, h in enumerate(hands):
        hands_view.append({
            'player': i,
            'tiles': h,
            'shanten': mahjong_app.shanten(h),
            'compact': mahjong_app.format_hand_compact(h),
        })

    # resultは従来通り（必要に応じてセッション管理も可能）
    result = mahjong_app.run_simulation(turns=turns)

    return render_template('index.html', result=result, turns=turns, hands_view=hands_view)


# 新しいルート: /discard
@app.route('/discard', methods=['POST'])
def discard():
    # セッションからwall, hands, 現在のプレイヤーを取得
    wall = session.get('wall')
    hands = session.get('hands')
    current_player = session.get('current_player', 0)

    if wall is None or hands is None:
        return jsonify({'error': 'No game in progress'}), 400

    # POSTデータからdiscard_indexを取得
    try:
        discard_index = int(request.form.get('discard_index'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid discard index'}), 400

    # 手牌から指定インデックスの牌を削除
    if discard_index < 0 or discard_index >= len(hands[current_player]):
        return jsonify({'error': 'Discard index out of range'}), 400
    discarded_tile = hands[current_player].pop(discard_index)
    # 捨てた後、必ずソート
    hands[current_player] = mahjong_app.sort_hand(hands[current_player])

    # 次のプレイヤー番号
    next_player = (current_player + 1) % 4

    # 山札が残っていれば次のプレイヤーが1枚引く
    drawn_tile = None
    if wall:
        drawn_tile = wall.pop()
        hands[next_player].append(drawn_tile)
        # ツモ直後に必ずソート
        hands[next_player] = mahjong_app.sort_hand(hands[next_player])

    # Player 1,2,3 の自動処理
    auto_log = []
    p = next_player
    while p != 0 and wall:
        # 最も効率的な捨て牌を選ぶ
        min_shanten = None
        best_discards = []
        for i in range(len(hands[p])):
            temp_hand = hands[p][:i] + hands[p][i+1:]
            s = mahjong_app.shanten(temp_hand)
            if (min_shanten is None) or (s < min_shanten):
                min_shanten = s
                best_discards = [i]
            elif s == min_shanten:
                best_discards.append(i)
        # 複数候補があればランダムに
        import random
        discard_i = random.choice(best_discards)
        auto_discarded = hands[p].pop(discard_i)
        # 捨てた後、必ずソート
        hands[p] = mahjong_app.sort_hand(hands[p])
        auto_log.append({'player': p, 'discarded': auto_discarded, 'shanten': min_shanten})
        # 次のプレイヤー
        p = (p + 1) % 4
        # 山札が残っていればツモ
        if wall and p != 0:
            auto_draw = wall.pop()
            hands[p].append(auto_draw)
            # ツモ直後に必ずソート
            hands[p] = mahjong_app.sort_hand(hands[p])
            auto_log[-1]['drawn'] = auto_draw

    # Player 0のツモ番
    player0_draw = None
    if wall and p == 0:
        player0_draw = wall.pop()
        hands[0].append(player0_draw)
        # ツモ直後に必ずソート
        hands[0] = mahjong_app.sort_hand(hands[0])

    # 各プレイヤーの最新シャンテン数リスト
    shanten_list = [mahjong_app.shanten(h) for h in hands]

    session['wall'] = wall
    session['hands'] = hands
    session['current_player'] = 0

    return jsonify({
        'discarded_tile': discarded_tile,
        'drawn_tile': drawn_tile,
        'auto_log': auto_log,
        'player0_draw': player0_draw,
        'next_player': 0,
        'hands': hands,
        'wall_count': len(wall),
        'shanten_list': shanten_list
    })


if __name__ == '__main__':
    app.run(debug=True)
