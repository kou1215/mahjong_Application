from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import mahjong_app
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    # セッションからデータ取得
    wall = session.get('wall')
    hands = session.get('hands')

    # ゲームが未開始、またはリセットが必要な場合
    if not wall or not hands:
        wall = mahjong_app.build_wall()
        hands = mahjong_app.deal(wall)
        # 手牌をソート（13枚）
        hands = [mahjong_app.sort_hand(h) for h in hands]
        
        # 親(Player 0)が最初の1枚をツモる
        drawn = wall.pop()
        hands[0].append(drawn) # 親は14枚スタート
        
        session['wall'] = wall
        session['hands'] = hands
        session['current_player'] = 0

    # Player 0のアガり判定（役があるか）
    hand_13 = hands[0][:-1]
    win_tile = hands[0][-1]
    agari_info = mahjong_app.evaluate_yaku(hand_13, win_tile)

    hands_view = []
    for i, h in enumerate(hands):
        hands_view.append({
            'player': i,
            'tiles': h,
            'shanten': mahjong_app.shanten(h),
            'compact': mahjong_app.format_hand_compact(h),
        })

    return render_template('index.html', 
                           hands_view=hands_view, 
                           wall_count=len(wall),
                           agari_info=agari_info)

@app.route('/discard', methods=['POST'])
def discard():
    wall = session.get('wall')
    hands = session.get('hands')
    
    if not wall or not hands:
        return jsonify({'error': 'No game in progress'}), 400

    try:
        discard_index = int(request.form.get('discard_index'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid discard index'}), 400

    # --- 1. Player 0 (人間) の打牌 ---
    discarded_tile = hands[0].pop(discard_index)
    hands[0] = mahjong_app.sort_hand(hands[0]) # 捨てた後に理牌

    auto_log = []
    
    # --- 2. Player 1, 2, 3 (AI) のターンを回す ---
    for p in range(1, 4):
        if not wall: break
        
        # ツモ
        drawn = wall.pop()
        hands[p].append(drawn)
        
        # AIのアガりチェック（簡易実装：アガりがあれば即終了など拡張可能）
        # ※今回はシャンテン数重視の打牌のみ
        
        # 最も効率的な捨て牌を選択（シャンテン数計算）
        min_shanten = 99
        best_indices = []
        for i in range(len(hands[p])):
            temp_hand = hands[p][:i] + hands[p][i+1:]
            s = mahjong_app.shanten(temp_hand)
            if s < min_shanten:
                min_shanten = s
                best_indices = [i]
            elif s == min_shanten:
                best_indices.append(i)
        
        idx = random.choice(best_indices)
        ai_discarded = hands[p].pop(idx)
        hands[p] = mahjong_app.sort_hand(hands[p])
        
        auto_log.append({
            'player': p,
            'drawn': drawn,
            'discarded': ai_discarded,
            'shanten': min_shanten
        })

    # --- 3. 再び Player 0 のツモ番 ---
    player0_draw = None
    agari_info = None
    if wall:
        player0_draw = wall.pop()
        hands[0].append(player0_draw)
        # アガり判定
        agari_info = mahjong_app.evaluate_yaku(hands[0][:-1], player0_draw)

    # セッション更新
    session['wall'] = wall
    session['hands'] = hands

    return jsonify({
        'player0_draw': player0_draw,
        'auto_log': auto_log,
        'hands': hands,
        'wall_count': len(wall),
        'shanten_list': [mahjong_app.shanten(h) for h in hands],
        'agari_info': agari_info
    })

if __name__ == '__main__':
    app.run(debug=True)