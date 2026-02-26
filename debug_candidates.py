#!/usr/bin/env python3
"""candidates リストの計算を確認するデバッグスクリプト"""

num_players = 4
discarer_id = 0  # Player 0 がディスカード

candidates = []
for i in range(1, num_players):
    pid = (discarer_id + i) % num_players
    candidates.append(pid)

print(f"discarer_id = {discarer_id}")
print(f"candidates = {candidates}")
print(f"Expected: [1, 2, 3]")
print()

# 別の discarer_id の場合
for test_discarer in range(4):
    test_candidates = []
    for i in range(1, num_players):
        pid = (test_discarer + i) % num_players
        test_candidates.append(pid)
    print(f"If discarer_id = {test_discarer}: candidates = {test_candidates}")
