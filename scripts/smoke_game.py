import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.game import Game

print('creating game')
g = Game()
print('starting game')
g.start_game()
print('wall count', len(g.wall))
res = g.process_discard(0)
print('process_discard returned keys:', list(res.keys()))
print('sample res:', {k: res[k] for k in res if k in ['discarded_tile','available_calls','auto_log']})
