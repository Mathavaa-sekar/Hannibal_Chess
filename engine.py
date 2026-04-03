"""
engine.py - Fixed & Optimized Chess AI Engine
Critical fix: evaluate() returns White-relative scores, but negamax needs
side-to-move-relative scores. Quiescence was using White-relative scores
directly, causing massive blunders when playing Black.
"""

import chess
import time
from collections import defaultdict

# ==================== Constants ====================
INF = 99999
MATE = 20000
MAX_PLY = 64
TT_SIZE = 500000
MAX_CHECK_EXT = 8

EXACT, LOWER, UPPER = 0, 1, 2

PIECE_VAL = [0, 100, 320, 330, 500, 900, 20000]

MVV_LVA = [[0] * 7 for _ in range(7)]
for _a in range(1, 7):
    for _v in range(1, 7):
        MVV_LVA[_v][_a] = PIECE_VAL[_v] * 10 - PIECE_VAL[_a]

# ==================== PST Tables ====================
PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]
BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]
ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]
KING_MG_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]
KING_EG_TABLE = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

PST = {
    chess.PAWN: PAWN_TABLE, chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE, chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE, chess.KING: KING_MG_TABLE,
}

# ==================== Hash Helper ====================
def _board_hash(board: chess.Board) -> int:
    try:
        return board.zobrist_hash()
    except AttributeError:
        try:
            import chess.polyglot
            return chess.polyglot.zobrist_hash(board)
        except (ImportError, AttributeError):
            return hash(
                board.board_fen() + " " + ("w" if board.turn else "b") +
                " " + board.castling_xfen() + " " +
                (chess.square_name(board.ep_square) if board.ep_square else "-")
            )

# ==================== Global State ====================
_tt: dict = {}
_killers: list = [[None, None] for _ in range(MAX_PLY)]
_history: dict = defaultdict(int)
_nodes: int = 0
_stop_time: float = 0
_stopped: bool = False


def new_game():
    """Clear ALL state including TT. Call when starting a new game."""
    global _tt, _killers, _history, _nodes, _stopped
    _tt.clear()
    _killers = [[None, None] for _ in range(MAX_PLY)]
    _history.clear()
    _nodes = 0
    _stopped = False


def _reset_search():
    """Reset per-move search state but KEEP TT for cross-move reuse."""
    global _killers, _history, _nodes, _stopped
    _killers = [[None, None] for _ in range(MAX_PLY)]
    _history.clear()
    _nodes = 0
    _stopped = False


# ==================== Evaluation ====================
def _is_endgame(board: chess.Board) -> bool:
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    if queens == 0:
        return True
    minors = (len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK)) +
              len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK)) +
              len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK)))
    return queens <= 2 and minors <= 2


def _pst_val(pt: int, sq: int, color: chess.Color, endgame: bool) -> int:
    table = KING_EG_TABLE if (pt == chess.KING and endgame) else PST[pt]
    idx = chess.square_mirror(sq) if color == chess.WHITE else sq
    return table[idx]


def _is_passed(board: chess.Board, sq: int, color: chess.Color) -> bool:
    rank = chess.square_rank(sq)
    file = chess.square_file(sq)
    enemy = not color
    if color == chess.WHITE:
        for r in range(rank + 1, 8):
            for f in range(max(0, file - 1), min(8, file + 2)):
                p = board.piece_at(chess.square(f, r))
                if p and p.piece_type == chess.PAWN and p.color == enemy:
                    return False
    else:
        for r in range(0, rank):
            for f in range(max(0, file - 1), min(8, file + 2)):
                p = board.piece_at(chess.square(f, r))
                if p and p.piece_type == chess.PAWN and p.color == enemy:
                    return False
    return True


def _king_safety(board: chess.Board, color: chess.Color) -> int:
    king_sq = board.king(color)
    if king_sq is None:
        return 0
    kf = chess.square_file(king_sq)
    kr = chess.square_rank(king_sq)
    safety = 0
    if color == chess.WHITE:
        if kr < 7:
            for f in range(max(0, kf - 1), min(8, kf + 2)):
                p = board.piece_at(chess.square(f, kr + 1))
                if p and p.piece_type == chess.PAWN and p.color == chess.WHITE:
                    safety += 12
    else:
        if kr > 0:
            for f in range(max(0, kf - 1), min(8, kf + 2)):
                p = board.piece_at(chess.square(f, kr - 1))
                if p and p.piece_type == chess.PAWN and p.color == chess.BLACK:
                    safety += 12
    is_open = True
    for r in range(8):
        p = board.piece_at(chess.square(kf, r))
        if p and p.piece_type == chess.PAWN:
            is_open = False
            break
    if is_open:
        safety -= 20
        for pt in (chess.ROOK, chess.QUEEN):
            if board.pieces(pt, not color):
                safety -= 15
                break
    return safety


def _has_bishop_pair(board: chess.Board, color: chess.Color) -> bool:
    bishops = list(board.pieces(chess.BISHOP, color))
    if len(bishops) < 2:
        return False
    c1 = (chess.square_file(bishops[0]) + chess.square_rank(bishops[0])) % 2
    c2 = (chess.square_file(bishops[1]) + chess.square_rank(bishops[1])) % 2
    return c1 != c2


def evaluate(board: chess.Board) -> int:
    """Evaluate position. ALWAYS returns positive = white advantage."""
    if board.is_checkmate():
        return -MATE if board.turn == chess.WHITE else MATE
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0
    endgame = _is_endgame(board)
    score = 0
    for pt in range(1, 7):
        for sq in board.pieces(pt, chess.WHITE):
            score += PIECE_VAL[pt] + _pst_val(pt, sq, chess.WHITE, endgame)
        for sq in board.pieces(pt, chess.BLACK):
            score -= PIECE_VAL[pt] + _pst_val(pt, sq, chess.BLACK, endgame)
    if _has_bishop_pair(board, chess.WHITE):
        score += 30
    if _has_bishop_pair(board, chess.BLACK):
        score -= 30
    for sq in board.pieces(chess.PAWN, chess.WHITE):
        if _is_passed(board, sq, chess.WHITE):
            score += 15 + chess.square_rank(sq) * 8
    for sq in board.pieces(chess.PAWN, chess.BLACK):
        if _is_passed(board, sq, chess.BLACK):
            score -= 15 + (7 - chess.square_rank(sq)) * 8
    if not endgame:
        score += _king_safety(board, chess.WHITE)
        score -= _king_safety(board, chess.BLACK)
    return score


def _eval_side(board: chess.Board) -> int:
    """Evaluate from the SIDE TO MOVE's perspective (for negamax)."""
    s = evaluate(board)
    return s if board.turn == chess.WHITE else -s


# ==================== Move Ordering ====================
def _score_move(board: chess.Board, move: chess.Move, tt_move: chess.Move, ply: int) -> int:
    if move == tt_move:
        return 10_000_000
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        v_pt = victim.piece_type if victim else chess.PAWN
        a_pt = attacker.piece_type if attacker else 0
        score += 1_000_000 + MVV_LVA[v_pt][a_pt]
    if move.promotion:
        score += 900_000 + PIECE_VAL[move.promotion]
    if ply < MAX_PLY:
        if move == _killers[ply][0]:
            score += 800_000
        elif move == _killers[ply][1]:
            score += 700_000
    score += _history.get((move.from_square, move.to_square), 0)
    return score


def _order_moves(board: chess.Board, tt_move: chess.Move, ply: int) -> list:
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: _score_move(board, m, tt_move, ply), reverse=True)
    return moves


def _store_killer(move: chess.Move, ply: int) -> None:
    if ply >= MAX_PLY:
        return
    if move != _killers[ply][0]:
        _killers[ply][1] = _killers[ply][0]
        _killers[ply][0] = move


# ==================== Quiescence Search ====================
def _quiesce(board: chess.Board, alpha: int, beta: int, ply: int) -> int:
    global _nodes
    _nodes += 1

    if _stopped or ply >= MAX_PLY:
        return _eval_side(board)

    # CRITICAL: use side-to-move perspective
    stand_pat = _eval_side(board)

    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    if ply > 8:
        return alpha

    for move in board.legal_moves:
        if not board.is_capture(move):
            continue
        # Delta pruning (stand_pat is already side-to-move relative)
        victim = board.piece_at(move.to_square)
        if victim and not move.promotion:
            if stand_pat + PIECE_VAL[victim.piece_type] + 200 < alpha:
                continue

        board.push(move)
        score = -_quiesce(board, -beta, -alpha, ply + 1)
        board.pop()

        if _stopped:
            return 0
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha


# ==================== Main Search (Negamax) ====================
def _negamax(board: chess.Board, depth: int, alpha: int, beta: int, ply: int,
             do_null: bool = True, ext: int = 0) -> int:
    global _nodes, _stopped

    _nodes += 1

    if (_nodes & 4095) == 0 and time.time() >= _stop_time:
        _stopped = True
        return 0
    if _stopped:
        return 0

    # Draw detection
    if ply > 0 and (board.is_repetition(2) or board.halfmove_clock >= 100):
        return 0

    # Terminal (side-to-move-relative by definition)
    if board.is_checkmate():
        return -MATE - ply
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    if depth <= 0:
        return _quiesce(board, alpha, beta, 0)

    in_check = board.is_check()

    # Check extension - CAPPED to prevent infinite extension chains
    if in_check and ext < MAX_CHECK_EXT:
        depth += 1
        ext += 1

    # ---- TT Lookup ----
    board_hash = _board_hash(board)
    tt_move = None
    tt_entry = _tt.get(board_hash)

    if tt_entry:
        tt_move, tt_val, tt_depth, tt_flag = tt_entry
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_val
            elif tt_flag == LOWER and tt_val >= beta:
                return tt_val
            elif tt_flag == UPPER and tt_val <= alpha:
                return tt_val

    # ---- Null Move Pruning (conservative) ----
    if do_null and not in_check and depth >= 4 and ply > 0:
        has_piece = False
        for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            if board.pieces(pt, board.turn):
                has_piece = True
                break
        if has_piece:
            board.push(chess.Move.null())
            R = 2 + (1 if depth > 6 else 0)
            null_val = -_negamax(board, depth - 1 - R, -beta, -beta + 1, ply + 1, False, ext)
            board.pop()
            if _stopped:
                return 0
            if null_val >= beta:
                return beta

    # ---- Generate & Order Moves ----
    moves = _order_moves(board, tt_move, ply)

    if not moves:
        return -MATE - ply if in_check else 0

    best_move = None
    best_val = -INF
    orig_alpha = alpha
    moves_searched = 0

    for move in moves:
        is_capture = board.is_capture(move)
        gives_check = board.gives_check(move)

        board.push(move)

        # LMR: only for late quiet moves, reduce by 1 max, safe conditions
        if (moves_searched >= 6 and depth >= 3 and not in_check
                and not gives_check and not is_capture and not move.promotion):
            score = -_negamax(board, depth - 2, -alpha - 1, -alpha, ply + 1, True, ext)
            if score > alpha and not _stopped:
                score = -_negamax(board, depth - 1, -beta, -alpha, ply + 1, True, ext)
        elif moves_searched > 0 and not is_capture and not move.promotion:
            # PVS null window
            score = -_negamax(board, depth - 1, -alpha - 1, -alpha, ply + 1, True, ext)
            if score > alpha and score < beta and not _stopped:
                score = -_negamax(board, depth - 1, -beta, -alpha, ply + 1, True, ext)
        else:
            # Full window: first move, captures, promotions
            score = -_negamax(board, depth - 1, -beta, -alpha, ply + 1, True, ext)

        board.pop()
        moves_searched += 1

        if _stopped:
            return 0

        if score > best_val:
            best_val = score
            best_move = move
        if score > alpha:
            alpha = score
        if alpha >= beta:
            if not is_capture:
                _store_killer(move, ply)
                key = (move.from_square, move.to_square)
                _history[key] = min(_history.get(key, 0) + depth * depth, 500000)
            break

    # ---- TT Store ----
    if best_val <= orig_alpha:
        tt_flag = UPPER
    elif best_val >= beta:
        tt_flag = LOWER
    else:
        tt_flag = EXACT

    if len(_tt) >= TT_SIZE:
        _tt.clear()
    _tt[board_hash] = (best_move, best_val, depth, tt_flag)

    return best_val


# ==================== Get Best Move ====================
def get_best_move(board: chess.Board, depth: int = 20, time_limit: float = 3.0) -> chess.Move:
    """Iterative deepening with time management."""
    global _stop_time, _stopped

    if board.is_game_over():
        return None

    _reset_search()
    _stop_time = time.time() + time_limit
    _stopped = False

    best_move = None
    start = time.time()

    for cur_depth in range(1, depth + 1):
        if time.time() >= _stop_time:
            break

        cur_best = None
        cur_val = -INF

        tt_move = None
        tt_entry = _tt.get(_board_hash(board))
        if tt_entry:
            tt_move = tt_entry[0]

        moves = _order_moves(board, tt_move, 0)
        if not moves:
            break

        for i, move in enumerate(moves):
            board.push(move)

            if i == 0:
                val = -_negamax(board, cur_depth - 1, -INF, INF, 1)
            else:
                # Proper PVS null window at root
                val = -_negamax(board, cur_depth - 1, -cur_val - 1, -cur_val, 1)
                if val > cur_val and not _stopped:
                    val = -_negamax(board, cur_depth - 1, -INF, INF, 1)

            board.pop()

            if _stopped:
                break
            if val > cur_val:
                cur_val = val
                cur_best = move

        if _stopped:
            if best_move:
                break
            elif cur_best:
                best_move = cur_best
            break

        if cur_best:
            best_move = cur_best

        elapsed = time.time() - start
        nps = int(_nodes / elapsed) if elapsed > 0.001 else 0
        print(f"[Engine] depth={cur_depth} eval={cur_val} nodes={_nodes} nps={nps} time={elapsed:.2f}s")

    total_time = time.time() - start
    print(f"[Engine] Best: {best_move} time={total_time:.2f}s")
    return best_move


# ==================== Display Evaluation ====================
def get_evaluation(board: chess.Board) -> dict:
    score = evaluate(board)
    if board.turn == chess.BLACK:
        score = -score
    if score > MATE - 100:
        label = f"#{(MATE - score + 1) // 2}"
    elif score < -(MATE - 100):
        label = f"-#{(MATE + score + 1) // 2}"
    else:
        label = f"+{score/100:.1f}" if score > 0 else (f"{score/100:.1f}" if score < 0 else "0.0")
    return {"score": score, "label": label}