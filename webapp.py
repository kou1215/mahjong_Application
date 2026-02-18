from flask import Flask, render_template, request
import mahjong_app

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    turns = 8
    hands_view = None
    if request.method == 'POST':
        try:
            turns = int(request.form.get('turns', 8))
        except ValueError:
            turns = 8
        # build a fresh deal for display (instead of textual simulation)
        wall = mahjong_app.build_wall()
        hands = mahjong_app.deal(wall)
        hands_view = []
        for i, h in enumerate(hands):
            sorted_tiles = mahjong_app.sort_hand(h)
            hands_view.append({
                'player': i,
                'tiles': sorted_tiles,
                'shanten': mahjong_app.shanten(h),
                'compact': mahjong_app.format_hand_compact(h),
            })
        result = mahjong_app.run_simulation(turns=turns)
    return render_template('index.html', result=result, turns=turns, hands_view=hands_view)


if __name__ == '__main__':
    app.run(debug=True)
