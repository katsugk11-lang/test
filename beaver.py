"""ビーバーが右か下にだけ進んで、最大いくつユリ(魚)を集められるかを求める。

1. 全探索: すべての経路を列挙して一番多いものを選ぶ
2. 動的計画法(DP): 各マスまでの最大値を順に埋めていく
"""
import itertools
import math
import random
import time

# 5x5 のマス。数字はそのマスにあるユリの数(左上がスタート、右下がゴール)
GRID = [
    [0, 2, 0, 1, 0],
    [1, 0, 3, 0, 2],
    [0, 2, 0, 1, 0],
    [3, 0, 1, 0, 2],
    [0, 1, 0, 2, 0],
]


def brute_force(grid):
    """全経路を列挙する。経路数は C(右+下, 右) 通り。"""
    h, w = len(grid), len(grid[0])
    best, best_path, count = -1, None, 0
    # 「右(R)を w-1 回、下(D)を h-1 回」の並べ方をすべて作る
    for right_steps in itertools.combinations(range(h + w - 2), w - 1):
        count += 1
        r = c = 0
        total = grid[0][0]
        path = [(0, 0)]
        for i in range(h + w - 2):
            if i in right_steps:
                c += 1
            else:
                r += 1
            total += grid[r][c]
            path.append((r, c))
        if total > best:
            best, best_path = total, path
    return best, best_path, count


def dp(grid):
    """dp[r][c] = (r, c) に着くまでに集められる最大数。"""
    h, w = len(grid), len(grid[0])
    best = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            from_up = best[r - 1][c] if r > 0 else 0
            from_left = best[r][c - 1] if c > 0 else 0
            best[r][c] = grid[r][c] + max(from_up, from_left)

    # ゴールから逆にたどって経路を復元する
    path = [(h - 1, w - 1)]
    r, c = h - 1, w - 1
    while (r, c) != (0, 0):
        if c == 0 or (r > 0 and best[r - 1][c] >= best[r][c - 1]):
            r -= 1
        else:
            c -= 1
        path.append((r, c))
    return best[h - 1][w - 1], path[::-1]


def show(grid, path):
    on_path = set(path)
    for r, row in enumerate(grid):
        print(" ".join(f"[{v}]" if (r, c) in on_path else f" {v} " for c, v in enumerate(row)))


if __name__ == "__main__":
    print("=== 5x5 ===")
    t = time.perf_counter()
    best, path, count = brute_force(GRID)
    print(f"全探索: 最大 {best} 個 / 調べた経路 {count} 通り ({time.perf_counter() - t:.6f} 秒)")
    t = time.perf_counter()
    best_dp, path_dp = dp(GRID)
    print(f"DP    : 最大 {best_dp} 個 ({time.perf_counter() - t:.6f} 秒)")
    show(GRID, path_dp)

    print("\n=== 50x50 ===")
    n = 50
    paths = math.comb(2 * (n - 1), n - 1)
    print(f"経路の数: {paths:,} 通り (約 {paths:.1e})")
    years = paths / 1e9 / (60 * 60 * 24 * 365)
    print(f"1秒に10億経路調べても約 {years:.1e} 年かかる → 全探索は無理")
    random.seed(0)
    big = [[random.randint(0, 3) for _ in range(n)] for _ in range(n)]
    t = time.perf_counter()
    best_big, _ = dp(big)
    print(f"DP なら: 最大 {best_big} 個 ({time.perf_counter() - t:.4f} 秒, 計算は {n * n} マス分だけ)")
