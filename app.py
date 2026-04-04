"""
app.py - Flask Backend for Chess Web App
"""

from flask import Flask, render_template, request, jsonify, session
import chess
import chess.pgn
import uuid
import os
from dotenv import load_dotenv
from engine import get_best_move, get_evaluation, new_game

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "chess_secret_key_change_in_production")

games: dict[str, chess.Board] = {}


def _send_email(subject, body):
    print(f"\n[LOG] {subject}\n{body}")


def _get_board() -> chess.Board:
    gid = session.get("game_id")
    if gid and gid in games:
        return games[gid]
    gid = str(uuid.uuid4())
    session["game_id"] = gid
    session["player_color"] = session.get("player_color", "white")
    games[gid] = chess.Board()
    return games[gid]


def _board_state(board: chess.Board) -> dict:
    pieces = {}
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            pieces[sq] = {
                "type": piece.piece_type,
                "color": "white" if piece.color == chess.WHITE else "black",
                "symbol": piece.symbol(),
            }

    start_counts = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1, chess.KING: 1}
    white_captured, black_captured = [], []
    for pt, cnt in start_counts.items():
        white_captured.extend([chess.piece_symbol(pt).upper()] * (cnt - len(board.pieces(pt, chess.WHITE))))
        black_captured.extend([chess.piece_symbol(pt).upper()] * (cnt - len(board.pieces(pt, chess.BLACK))))

    temp = chess.Board()
    history = []
    for move in board.move_stack:
        history.append(temp.san(move))
        temp.push(move)

    status, result_msg = "playing", ""
    if board.is_checkmate():
        status = "checkmate"
        winner = "Black" if board.turn == chess.WHITE else "White"
        result_msg = f"Checkmate — {winner} wins!"
    elif board.is_stalemate():
        status, result_msg = "draw", "Stalemate — Draw"
    elif board.is_insufficient_material():
        status, result_msg = "draw", "Insufficient material — Draw"
    elif board.can_claim_fifty_moves():
        status, result_msg = "draw", "Fifty-move rule — Draw"
    elif board.can_claim_threefold_repetition():
        status, result_msg = "draw", "Threefold repetition — Draw"
    elif board.is_check():
        status, result_msg = "check", "Check!"

    eval_data = get_evaluation(board)

    pgn_str = None
    winner_color = None
    if status in ("checkmate", "draw"):
        pgn_game = chess.pgn.Game()
        node = pgn_game
        for move in board.move_stack:
            node = node.add_variation(move)
        if status == "checkmate":
            pgn_game.headers["Result"] = "1-0" if board.turn == chess.BLACK else "0-1"
            winner_color = "black" if board.turn == chess.WHITE else "white"
        else:
            pgn_game.headers["Result"] = "1/2-1/2"
        pgn_str = str(pgn_game)
        if status == "checkmate":
            side = winner_color.capitalize()
            print(f"\n{'='*50}")
            print(f"  GAME OVER — Checkmate")
            print(f"  Winner: {side}")
            print(f"{'='*50}")
            print(pgn_str)
            print(f"{'='*50}\n")
        else:
            print(f"\n{'='*50}")
            print(f"  GAME OVER — Draw")
            print(f"{'='*50}")
            print(pgn_str)
            print(f"{'='*50}\n")

    return {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "pieces": pieces,
        "status": status,
        "result_msg": result_msg,
        "history": history,
        "white_captured": white_captured,
        "black_captured": black_captured,
        "eval_label": eval_data["label"],
        "eval_score": eval_data["score"],
        "move_number": board.fullmove_number,
        "last_move": {
            "from": board.peek().from_square,
            "to": board.peek().to_square,
        } if board.move_stack else None,
        "pgn": pgn_str,
        "winner_color": winner_color,
        "checkers": list(board.checkers()),
    }


def _send_game_over_email(state):
    player_name = session.get("player_name", "Unknown")
    player_color = session.get("player_color", "?")
    winner_color = state.get("winner_color")

    if state["status"] == "checkmate" and winner_color:
        if winner_color == player_color:
            result_text = f"{player_name} won against Hannibal Bot!"
        else:
            result_text = f"Hannibal Bot won against {player_name}!"
    else:
        result_text = f"Draw! ({player_name} as {player_color.capitalize()})"

    _send_email(
        f"[Hannibal] Game Over — {result_text}",
        f"Player: {player_name}\nColor: {player_color.capitalize()}\nResult: {result_text}\n\nPGN:\n{state['pgn']}"
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new_game", methods=["POST"])
def new_game_route():
    data = request.get_json() or {}
    player_color = data.get("color", "white")
    if player_color not in ("white", "black"):
        player_color = "white"

    player_name = data.get("name", "Unknown")

    gid = str(uuid.uuid4())
    session["game_id"] = gid
    session["player_color"] = player_color
    session["player_name"] = player_name
    session["game_logged"] = False
    games[gid] = chess.Board()
    new_game()

    board = games[gid]
    ai_move_uci = None
    ai_capture = False
    ai_check = False

    # If player is black, AI (white) moves first
    if player_color == "black":
        piece_count = len(board.piece_map())
        if piece_count <= 10:
            time_limit = 5.0
        elif piece_count <= 20:
            time_limit = 20.0
        else:
            time_limit = 15.0
        ai_move = get_best_move(board, depth=20, time_limit=time_limit)
        if ai_move:
            ai_capture = board.is_capture(ai_move)
            board.push(ai_move)
            ai_check = board.is_check()
            ai_move_uci = ai_move.uci()

    return jsonify({
        "ok": True,
        "state": _board_state(board),
        "player_color": player_color,
        "ai_move": ai_move_uci,
        "ai_capture": ai_capture,
        "ai_check": ai_check,
    })


@app.route("/api/state", methods=["GET"])
def get_state():
    board = _get_board()
    return jsonify({
        "ok": True,
        "state": _board_state(board),
        "player_color": session.get("player_color", "white"),
    })


@app.route("/api/legal_moves", methods=["GET"])
def legal_moves():
    try:
        sq = int(request.args.get("square", ""))
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid square"}), 400
    board = _get_board()
    destinations = [m.to_square for m in board.legal_moves if m.from_square == sq]
    return jsonify({"ok": True, "destinations": destinations})


@app.route("/api/move", methods=["POST"])
def make_move():
    data = request.get_json()
    from_sq = data.get("from")
    to_sq = data.get("to")
    promo = data.get("promotion")
    board = _get_board()

    # Always keep name in session (fixes "Unknown" issue)
    player_name = data.get("name")
    if player_name:
        session["player_name"] = player_name

    if board.is_game_over():
        return jsonify({"ok": False, "error": "Game is already over."})

    promo_piece = chess.Piece.from_symbol(promo).piece_type if promo else None

    if not promo_piece:
        piece = board.piece_at(from_sq)
        if piece and piece.piece_type == chess.PAWN:
            rank = chess.square_rank(to_sq)
            if (piece.color == chess.WHITE and rank == 7) or (piece.color == chess.BLACK and rank == 0):
                promo_piece = chess.QUEEN

    move = chess.Move(from_sq, to_sq, promotion=promo_piece)

    if move not in board.legal_moves:
        return jsonify({"ok": False, "error": "Illegal move."})

    # Send "game started" email on FIRST move only
    if not session.get("game_logged"):
        name = session.get("player_name", "Unknown")
        color = session.get("player_color", "?")
        _send_email(
            f"[Hannibal] | New Game — {name} as {color.capitalize()}",
            f"Player: {name}\nColor: {color.capitalize()}\n\nFirst move played."
        )
        session["game_logged"] = True

    human_capture = board.is_capture(move)
    board.push(move)
    human_check = board.is_check()

    if board.is_game_over():
        state = _board_state(board)
        if state["pgn"]:
            _send_game_over_email(state)
        return jsonify({
            "ok": True,
            "state": state,
            "ai_move": None,
            "human_capture": human_capture,
            "human_check": human_check,
            "ai_capture": False,
            "ai_check": False,
        })

    piece_count = len(board.piece_map())
    if piece_count <= 10:
        time_limit = 5.0
    elif piece_count <= 20:
        time_limit = 3.0
    else:
        time_limit = 2.5

    ai_move = get_best_move(board, depth=20, time_limit=time_limit)
    ai_capture, ai_check = False, False
    if ai_move:
        ai_capture = board.is_capture(ai_move)
        board.push(ai_move)
        ai_check = board.is_check()

    state = _board_state(board)

    if state["status"] in ("checkmate", "draw") and state["pgn"]:
        _send_game_over_email(state)

    return jsonify({
        "ok": True,
        "state": state,
        "ai_move": ai_move.uci() if ai_move else None,
        "human_capture": human_capture,
        "human_check": human_check,
        "ai_capture": ai_capture,
        "ai_check": ai_check,
    })

if __name__ == "__main__":
    print("♟  Chess App → http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)