from flask import Flask, render_template, request
import mahjong_app

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    turns = 8
    if request.method == 'POST':
        try:
            turns = int(request.form.get('turns', 8))
        except ValueError:
            turns = 8
        result = mahjong_app.run_simulation(turns=turns)
    return render_template('index.html', result=result, turns=turns)


if __name__ == '__main__':
    app.run(debug=True)
