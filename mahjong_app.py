import random
from collections import Counter
from functools import lru_cache
import importlib

# --- mahjong ライブラリのインポート（役計算・シャンテン計算用） ---
try:
    _mahjong_lib = importlib.import_module('mahjong')
    from mahjong.hand_calculating.hand import HandCalculator
    from mahjong.tile import TilesConverter
    from mahjong.hand_calculating.hand_config import HandConfig
    _MAHJONG_AVAILABLE = True
except Exception:
    _MAHJONG_AVAILABLE = False
    print("【警告】mahjongライブラリが見つかりません。役の計算には 'pip install mahjong' が必要です。")

# === 基本機能（山作り・配牌・ソート） ===
def build_wall():
    suits = ['m', 'p', 's']
    tiles = []
    for s in suits:
        for n in range(1, 10):
            tiles.append(f"{n}{s}")
    honors = ['E', 'S', 'W', 'N', 'P', 'F', 'C']
    tiles += honors
    wall = []
    for t in tiles:
        wall.extend([t] * 4)
    random.shuffle(wall)
    return wall

def deal(wall):
    hands = [[] for _ in range(4)]
    for _ in range(13):
        for p in range(4):
            hands[p].append(wall.pop())
    # 親(Player 0)の14枚目は「ツモ」アクションとして扱うため、ここでは13枚にしておきます
    return hands

def sort_hand(hand):
    order = {}
    idx = 0
    for s in ['m', 'p', 's']:
        for n in range(1, 10):
            order[f"{n}{s}"] = idx
            idx += 1
    for h in ['E', 'S', 'W', 'N', 'P', 'F', 'C']:
        order[h] = idx
        idx += 1
    return sorted(hand, key=lambda t: order.get(t, 999))
    
def format_hand_compact(hand):
    suits = {'m': [], 'p': [], 's': []}
    honors = []
    for t in sort_hand(hand):
        if len(t) == 2 and t[1] in suits:
            suits[t[1]].append(t[0])
        else:
            honors.append(t)
    parts = []
    for s in ['m', 'p', 's']:
        if suits[s]:
            parts.append(''.join(suits[s]) + s)
    if honors:
        parts.append(' '.join(honors))
    return ' '.join(parts)


# === シャンテン数計算（復元） ===
def _build_index_map():
    order = {}
    idx = 0
    for s in ['m', 'p', 's']:
        for n in range(1, 10):
            order[f"{n}{s}"] = idx
            idx += 1
    for h in ['E', 'S', 'W', 'N', 'P', 'F', 'C']:
        order[h] = idx
        idx += 1
    return order

TILE_INDEX = _build_index_map()
INDEX_TILE = {v: k for k, v in TILE_INDEX.items()}

def hand_to_counts(hand):
    counts = [0] * 34
    for t in hand:
        i = TILE_INDEX.get(t)
        if i is not None:
            counts[i] += 1
    return counts

@lru_cache(maxsize=2048)
def _suit_best(counts_tuple):
    counts = list(counts_tuple)
    best_m = 0
    best_t = 0

    def dfs(pos, m, t):
        nonlocal best_m, best_t
        while pos < 9 and counts[pos] == 0:
            pos += 1
        if pos >= 9:
            if m + t > best_m + best_t:
                best_m, best_t = m, t
            return
        if counts[pos] >= 3:
            counts[pos] -= 3
            dfs(pos, m + 1, t)
            counts[pos] += 3
        if pos <= 6 and counts[pos] and counts[pos + 1] and counts[pos + 2]:
            counts[pos] -= 1
            counts[pos + 1] -= 1
            counts[pos + 2] -= 1
            dfs(pos, m + 1, t)
            counts[pos] += 1
            counts[pos + 1] += 1
            counts[pos + 2] += 1
        if counts[pos] >= 2:
            counts[pos] -= 2
            dfs(pos, m, t + 1)
            counts[pos] += 2
        if pos <= 7 and counts[pos] and counts[pos + 1]:
            counts[pos] -= 1
            counts[pos + 1] -= 1
            dfs(pos, m, t + 1)
            counts[pos] += 1
            counts[pos + 1] += 1
        c = counts[pos]
        counts[pos] = 0
        dfs(pos + 1, m, t)
        counts[pos] = c

    dfs(0, 0, 0)
    return best_m, best_t

def shanten_standard(counts):
    min_shanten = 8
    for i in range(34):
        if counts[i] >= 2:
            c = list(counts)
            c[i] -= 2
            m = 0
            t = 0
            for j in range(27, 34):
                if c[j] >= 3:
                    m += c[j] // 3
            for s in range(3):
                off = s * 9
                suit_counts = tuple(c[off:off + 9])
                sm, st = _suit_best(suit_counts)
                m += sm
                t += st
            sh = 8 - m * 2 - t - 1
            if sh < min_shanten:
                min_shanten = sh
    c = list(counts)
    m = 0
    t = 0
    for j in range(27, 34):
        if c[j] >= 3:
            m += c[j] // 3
    for s in range(3):
        off = s * 9
        suit_counts = tuple(c[off:off + 9])
        sm, st = _suit_best(suit_counts)
        m += sm
        t += st
    sh = 8 - m * 2 - t
    if sh < min_shanten:
        min_shanten = sh
    return min_shanten

def shanten_chiitoitsu(counts):
    pairs = sum(1 for c in counts if c >= 2)
    blocks = sum(1 for c in counts if c > 0)
    sh = 6 - pairs + max(0, 7 - blocks)
    return sh

def shanten_kokushi(counts):
    terminals = [0, 8, 9, 17, 18, 26]
    honors_idx = list(range(27, 34))
    uniques = 0
    pair = False
    for i in terminals + honors_idx:
        if counts[i] > 0:
            uniques += 1
        if counts[i] >= 2:
            pair = True
    sh = 13 - uniques - (1 if pair else 0)
    return sh

def shanten(hand):
    if _MAHJONG_AVAILABLE:
        try:
            try:
                from mahjong.shanten import Shanten
                sh = Shanten()
                return sh.calculate_shanten(hand)
            except Exception:
                try:
                    from mahjong import shanten as sh_mod
                    if hasattr(sh_mod, 'calculate_shanten'):
                        return sh_mod.calculate_shanten(hand)
                    if hasattr(sh_mod, 'shanten'):
                        return sh_mod.shanten(hand)
                except Exception:
                    pass
        except Exception:
            pass
    counts = hand_to_counts(hand)
    s_std = shanten_standard(counts)
    s_chi = shanten_chiitoitsu(counts)
    s_kok = shanten_kokushi(counts)
    return min(s_std, s_chi, s_kok)


# === 役・アガり計算機能 ===
HONOR_TO_Z = {'E': '1', 'S': '2', 'W': '3', 'N': '4', 'P': '5', 'F': '6', 'C': '7'}

def convert_to_136_array(hand):
    man, pin, sou, honors = "", "", "", ""
    for t in hand:
        if 'm' in t: man += t[0]
        elif 'p' in t: pin += t[0]
        elif 's' in t: sou += t[0]
        else: honors += HONOR_TO_Z.get(t, '')
    return TilesConverter.string_to_136_array(man=man, pin=pin, sou=sou, honors=honors)

def evaluate_yaku(hand_13, win_tile, is_tsumo=True):
    if not _MAHJONG_AVAILABLE:
        return {"is_agari": False, "error": "mahjong library is not installed."}
    try:
        calculator = HandCalculator()
        config = HandConfig(is_tsumo=is_tsumo)
        all_tiles = hand_13 + [win_tile]
        tiles_136 = convert_to_136_array(all_tiles)
        win_tile_136 = tiles_136[-1] 
        result = calculator.estimate_hand_value(tiles_136, win_tile_136, config=config)
        
        if result.error:
            return {"is_agari": False, "reason": result.error}
        
        return {
            "is_agari": True,
            "han": result.han,
            "fu": result.fu,
            "cost": result.cost,
            "yaku": [yaku.name for yaku in result.yaku]
        }
    except Exception as e:
        return {"is_agari": False, "error": str(e)}


# === ゲームのアクション機能 ===
def draw_tile(wall, hand):
    if not wall:
        return None
    drawn = wall.pop()
    hand.append(drawn)
    return drawn

def discard_tile(hand, index):
    if 0 <= index < len(hand):
        return hand.pop(index)
    return None