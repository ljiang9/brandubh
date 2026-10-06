"""爱尔兰 Brandubh（7x7 tafl）：国王突围 vs 攻方围杀。纯标准库。"""

import argparse
import copy
import random
import sys

SIZE = 7
THRONE = (3, 3)
CORNERS = {(0, 0), (0, 6), (6, 0), (6, 6)}

EMPTY = 0
ATTACKER = 1   # 攻方（8 子）
DEFENDER = 2   # 守方（4 子）
KING = 3       # 国王

GLYPH = {EMPTY: "·", ATTACKER: "▲", DEFENDER: "●", KING: "♔"}
DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def other(side):
    return DEFENDER if side == ATTACKER else ATTACKER


def is_def_side(piece):
    return piece in (DEFENDER, KING)


class Brandubh:
    """7x7 棋盘。攻方先手（传统 tafl 攻方先走）。"""

    def __init__(self):
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        # 国王与守方
        self.board[3][3] = KING
        for r, c in [(2, 3), (4, 3), (3, 2), (3, 4)]:
            self.board[r][c] = DEFENDER
        # 攻方 8 子
        for r, c in [(0, 3), (1, 3), (5, 3), (6, 3),
                     (3, 0), (3, 1), (3, 5), (3, 6)]:
            self.board[r][c] = ATTACKER
        self.turn = ATTACKER
        self.winner = None          # "attackers" / "defenders"
        self.n_moves = 0
        self.king_pos = (3, 3)

    # ---------- 基础 ----------

    def in_bounds(self, r, c):
        return 0 <= r < SIZE and 0 <= c < SIZE

    def piece_at(self, r, c):
        return self.board[r][c]

    def _is_hostile_to(self, r, c, side):
        """(r,c) 格是否可作为 side 夹吃的另一颚（王座对攻方敌对）。"""
        if not self.in_bounds(r, c):
            return False
        p = self.board[r][c]
        if (r, c) == THRONE and side == DEFENDER:
            return True  # 王座对攻方敌对：守方可借王座夹吃
        if side == ATTACKER:
            return p == ATTACKER
        return p in (DEFENDER, KING)

    # ---------- 走法 ----------

    def legal_moves(self, side):
        """side 所有合法走法：[(fr,fc,tr,tc)]，车式走法，不可跳子；
        非王不可进入王座与角落。"""
        moves = []
        for fr in range(SIZE):
            for fc in range(SIZE):
                p = self.board[fr][fc]
                if p == EMPTY:
                    continue
                if side == ATTACKER and p != ATTACKER:
                    continue
                if side == DEFENDER and not is_def_side(p):
                    continue
                is_king = (p == KING)
                for dr, dc in DIRS:
                    r, c = fr + dr, fc + dc
                    while self.in_bounds(r, c) and self.board[r][c] == EMPTY:
                        if (r, c) == THRONE or (r, c) in CORNERS:
                            if not is_king:
                                break  # 非王不可进入王座/角落
                        moves.append((fr, fc, r, c))
                        if (r, c) == THRONE or (r, c) in CORNERS:
                            break
                        r, c = r + dr, c + dc
        return moves

    def apply_move(self, move):
        """执行走法并结算吃子/胜负。非法抛 ValueError。"""
        fr, fc, tr, tc = move
        p = self.board[fr][fc]
        side = self.turn
        if side == ATTACKER and p != ATTACKER:
            raise ValueError("攻方回合只能走攻子")
        if side == DEFENDER and not is_def_side(p):
            raise ValueError("守方回合只能走守子/王")
        if (fr, fc) == (tr, tc) or fr != tr and fc != tc:
            raise ValueError("只能横竖走")
        if not self.in_bounds(tr, tc):
            raise ValueError("落点越界")
        if self.board[tr][tc] != EMPTY:
            raise ValueError("落点被占")
        if ((tr, tc) == THRONE or (tr, tc) in CORNERS) and p != KING:
            raise ValueError("非王不可进王座/角落")
        # 路径畅通
        dr = 0 if tr == fr else (1 if tr > fr else -1)
        dc = 0 if tc == fc else (1 if tc > fc else -1)
        r, c = fr + dr, fc + dc
        while (r, c) != (tr, tc):
            if self.board[r][c] != EMPTY:
                raise ValueError("路径被挡")
            r, c = r + dr, c + dc

        self.board[fr][fc] = EMPTY
        self.board[tr][tc] = p
        if p == KING:
            self.king_pos = (tr, tc)
        self.n_moves += 1

        # 王到角落：守方胜
        if p == KING and (tr, tc) in CORNERS:
            self.winner = "defenders"
            return

        # 夹吃：落子相邻敌子、另一侧是己方/敌对格（王座对攻方敌对）
        for dr, dc in DIRS:
            nr, nc = tr + dr, tc + dc
            br, bc = nr + dr, nc + dc
            if not self.in_bounds(nr, nc):
                continue
            q = self.board[nr][nc]
            if q == EMPTY or q == KING:
                continue
            if side == ATTACKER and q != DEFENDER:
                continue
            if side == DEFENDER and q != ATTACKER:
                continue
            if self._is_hostile_to(br, bc, side):
                self.board[nr][nc] = EMPTY

        # 王被吃：四面被攻子包围（王座不算敌对格）
        kr, kc = self.king_pos
        if self.board[kr][kc] == KING:
            surrounded = all(
                self.in_bounds(kr + dr, kc + dc)
                and self.board[kr + dr][kc + dc] == ATTACKER
                for dr, dc in DIRS
            )
            if surrounded:
                self.winner = "attackers"

        # 无棋可走判负
        if self.winner is None:
            self.turn = other(side)
            if not self.legal_moves(self.turn):
                self.winner = "attackers" if self.turn == DEFENDER else "defenders"

    def is_over(self):
        return self.winner is not None

    # ---------- 渲染 ----------

    def render(self):
        lines = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                if (r, c) == THRONE and self.board[r][c] == EMPTY:
                    row.append("✛")
                elif (r, c) in CORNERS and self.board[r][c] == EMPTY:
                    row.append("◇")
                else:
                    row.append(GLYPH[self.board[r][c]])
            lines.append(" ".join(row))
        return "\n".join(lines)


# ---------- AI ----------

def ai_choose(game, seed_rng):
    moves = game.legal_moves(game.turn)
    if not moves:
        return None
    side = game.turn
    # 贪心：胜局 > 吃子数 > 随机；王走优先逃向角落加分
    scored = []
    for m in moves:
        g2 = copy.deepcopy(game)
        before = sum(row.count(ATTACKER if side == DEFENDER else DEFENDER)
                     for row in g2.board)
        g2.apply_move(m)
        after = sum(row.count(ATTACKER if side == DEFENDER else DEFENDER)
                    for row in g2.board)
        capture = before - after
        win = 100 if g2.winner == ("defenders" if side == DEFENDER else "attackers") else 0
        king_bonus = 0
        if game.board[m[0]][m[1]] == KING:
            d0 = min(abs(m[0] - cr) + abs(m[1] - cc) for cr, cc in CORNERS)
            d1 = min(abs(m[2] - cr) + abs(m[3] - cc) for cr, cc in CORNERS)
            king_bonus = (d0 - d1) * 5  # 王越接近角落越好
        scored.append((win + capture * 10 + king_bonus + seed_rng.random(), m))
    scored.sort(reverse=True)
    return scored[0][1]


def play_auto(games, seed):
    rng = random.Random(seed)
    res = {"attackers": 0, "defenders": 0, "draw": 0}
    for _ in range(games):
        g = Brandubh()
        steps = 0
        while not g.is_over() and steps < 400:
            m = ai_choose(g, rng)
            if m is None:
                break
            g.apply_move(m)
            steps += 1
        if g.winner == "attackers":
            res["attackers"] += 1
        elif g.winner == "defenders":
            res["defenders"] += 1
        else:
            res["draw"] += 1
    return res


def play_interactive():
    if not sys.stdin.isatty():
        print("交互模式需要终端；无头演示请用 --auto", file=sys.stderr)
        sys.exit(2)
    g = Brandubh()
    print("Brandubh 爱尔兰棋：攻方▲先手围王，守方●/♔把王送到角落◇即胜。")
    print("走法格式：起点行列 终点行列，如 03 33（行列均为0-6）")
    print(g.render())
    while not g.is_over():
        side = "攻方▲" if g.turn == ATTACKER else "守方●"
        try:
            s = input(f"{side}走> ").strip().replace(" ", "")
        except EOFError:
            break
        if s in ("q", "退出"):
            break
        if len(s) != 4 or not s.isdigit():
            print("格式错误，例：0333")
            continue
        fr, fc, tr, tc = map(int, s)
        try:
            g.apply_move((fr, fc, tr, tc))
        except ValueError as e:
            print("非法：", e)
            continue
        print(g.render())
    if g.winner == "attackers":
        print("攻方胜：国王被擒！")
    elif g.winner == "defenders":
        print("守方胜：国王突围！")
    else:
        print("对局结束。")


def main():
    ap = argparse.ArgumentParser(description="Brandubh 爱尔兰 7x7 tafl")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.auto:
        res = play_auto(args.games, args.seed)
        print(f"共 {args.games} 局：攻方胜 {res['attackers']}，"
              f"守方胜 {res['defenders']}，和棋 {res['draw']}")
    else:
        play_interactive()


if __name__ == "__main__":
    main()
