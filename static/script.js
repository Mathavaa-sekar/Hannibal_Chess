/**
 * script.js — Deep Knight Chess Frontend
 *
 * Supports playing as White or Black.
 * When playing as Black the board is flipped and the AI moves first.
 *
 * Key behaviours:
 *  1. Human move is shown on the board IMMEDIATELY (optimistic render)
 *  2. AI thinking indicator plays while the server computes
 *  3. AI move is applied once the server responds
 *  4. Sounds: move · capture · check · game-end  (Web Audio API, no files needed)
 */

"use strict";

// ── SVG piece paths (Colin M.L. Burnett / CC BY-SA 3.0) ──────────────────────
const PATHS = {
  6: [
    'M22.5 11.63V6',
    'M20 8h5',
    'M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5z',
    'M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z'
  ],
  5: [
    'M9 26c8.5-1.5 21-1.5 27 0l2-12-7 11V11l-5.5 13.5-3-15-3 15L14 11v14L7 14l2 12z',
    'M9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4z'
  ],
  4: [
    'M9 39h27v-3H9z',
    'M12.5 32l1.5-2.5h17l1.5 2.5z',
    'M12 36v-4h21v4H12z',
    'M14 29.5v-13h17v13H14z',
    'M14 16.5L11 14h23l-3 2.5H14z',
    'M11 14V9h4v2h5V9h5v2h5V9h4v5H11z'
  ],
  3: [
    'M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2z',
    'M15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2z',
    'M17 15L21 20',
    'M25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z'
  ],
  2: [
    'M22 10c10.5 1 16.5 8 16 29H15c0-9 10-6.5 8-21z',
    'M24 18c.38 2.91-5.55 7.37-8 9-3 2-2.82 4.34-5 4-1.042-.94 1.41-3.04 0-3-1 0 .19 1.23-1 2-1 0-4.003 1-4-4 0-2 6-12 6-12s1.89-1.9 2-3.5c-.73-.994-.5-2-.5-3 1-1 3 2.5 3 2.5h2s.78-1.992 2.5-3c1 0 1 3 1 3z'
  ],
  1: [
    'M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03C15.41 27.09 11 31.58 11 39.5H34C34 31.58 29.59 27.09 26.59 26.03A6.006 6.006 0 0 0 29 21c0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z'
  ]
};

const CAP_TYPE = { P: 1, N: 2, B: 3, R: 4, Q: 5 };

function pieceSVG(type, color) {
  const w = color === 'white';
  const fill   = w ? '#f0e6d3' : '#2a2420';
  const stroke = w ? '#2a2420' : '#FFFFFF';
  const sw     = w ? 1.5 : 1.3;
  const paths  = PATHS[type] || [];
  let inner  = paths.map(d => `<path d="${d}"/>`).join('');
  if (type === 5) inner += `<circle cx="38" cy="14" r="1.5"/><circle cx="31" cy="11" r="1.5"/><circle cx="22.5" cy="9.5" r="1.5"/><circle cx="14" cy="11" r="1.5"/><circle cx="7" cy="14" r="1.5"/>`;
  return `<svg class="piece-svg" viewBox="0 0 45 45"><g fill="${fill}" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${inner}</g></svg>`;
}

function capPieceSVG(type, color) {
  const w = color === 'white';
  const fill   = w ? '#f0e6d3' : '#2a2420';
  const stroke = w ? '#2a2420' : '#FFFFFF';
  const sw     = w ? 1.8 : 1.5;
  const paths  = PATHS[type] || [];
  const inner  = paths.map(d => `<path d="${d}"/>`).join('');
  return `<svg class="cap-piece-svg" viewBox="0 0 45 45"><g fill="${fill}" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${inner}</g></svg>`;
}

// ── Web Audio sound synthesiser ─────────────────────────────────────────────
const audio = (() => {
  let ctx = null;
  function getCtx() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  function tone(freq, type, gain, duration) {
    const ac  = getCtx();
    const osc = ac.createOscillator();
    const amp = ac.createGain();
    osc.connect(amp); amp.connect(ac.destination);
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ac.currentTime);
    amp.gain.setValueAtTime(gain, ac.currentTime);
    amp.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
    osc.start(ac.currentTime); osc.stop(ac.currentTime + duration);
  }
  function noise(duration, gainVal, freq = 800, q = 2.0) {
    const ac     = getCtx();
    const buf    = ac.createBuffer(1, ac.sampleRate * duration, ac.sampleRate);
    const data   = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1);
    const src    = ac.createBufferSource(); src.buffer = buf;
    const filter = ac.createBiquadFilter(); 
    filter.type = "bandpass";
    filter.frequency.value = freq;
    filter.Q.value = q;
    const amp    = ac.createGain();
    amp.gain.setValueAtTime(gainVal, ac.currentTime);
    amp.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + duration);
    src.connect(filter); filter.connect(amp); amp.connect(ac.destination);
    src.start(); src.stop(ac.currentTime + duration);
  }
  return {
    move()    { tone(600, "sine", 0.45, 0.05); noise(0.05, 0.25, 500, 2.0); },
    capture() { tone(400, "sine", 0.60, 0.10); noise(0.10, 0.70, 300, 2.0); },
    check()   { tone(523.25, "sine", 0.40, 0.30); setTimeout(() => tone(659.25, "sine", 0.35, 0.30), 150); },
    gameEnd() { 
      setTimeout(() => tone(523.25, "sine", 0.35, 0.50), 0); 
      setTimeout(() => tone(659.25, "sine", 0.30, 0.50), 180); 
      setTimeout(() => tone(698.46, "sine", 0.25, 0.50), 360); 
      setTimeout(() => tone(783.99, "sine", 0.20, 0.60), 540); 
    },
  };
})();

// ── DOM refs ────────────────────────────────────────────────────────────────
const boardEl       = document.getElementById("board");
const rankLabels    = document.getElementById("rankLabels");
const fileLabels    = document.getElementById("fileLabels");
const historyBody   = document.getElementById("historyBody");
const evalScore     = document.getElementById("evalScore");
const evalWhiteFill = document.getElementById("evalWhiteFill");
const evalBlackFill = document.getElementById("evalBlackFill");
const whiteCap      = document.getElementById("whiteCaptured");
const blackCap      = document.getElementById("blackCaptured");
const statusMsg     = document.getElementById("statusMsg");
const playerWhite   = document.getElementById("playerWhite");
const playerBlack   = document.getElementById("playerBlack");
const nameWhite     = document.getElementById("nameWhite");
const nameBlack     = document.getElementById("nameBlack");
const turnSubWhite  = document.getElementById("turnSubWhite");
const turnSubBlack  = document.getElementById("turnSubBlack");
const thinkingDotsW = document.getElementById("thinkingDotsWhite");
const thinkingDotsB = document.getElementById("thinkingDotsBlack");
const btnPlayWhite  = document.getElementById("btnPlayWhite");
const btnPlayBlack  = document.getElementById("btnPlayBlack");
const promoOverlay  = document.getElementById("promoOverlay");
const promoOptions  = document.getElementById("promoOptions");
const pgnArea       = document.getElementById("pgnArea");
const pgnText       = document.getElementById("pgnText");

// ── Username ─────────────────────────────────────────────────────────────────
let userName = localStorage.getItem("chess_username");

function _showNameModal(titleText) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("nameOverlay");
    const input   = document.getElementById("nameInput");
    const btn     = document.getElementById("nameBtn");
    const title   = overlay.querySelector(".name-title");

    title.textContent = titleText;
    input.value = userName || "";
    overlay.classList.remove("hidden");
    setTimeout(() => input.focus(), 50);

    function submit() {
      const val = input.value.trim();
      if (!val) {
        input.style.borderColor = "#b03020";
        return;
      }
      userName = val;
      localStorage.setItem("chess_username", userName);
      overlay.classList.add("hidden");
      btn.removeEventListener("click", submit);
      input.removeEventListener("keydown", onKey);
      resolve();
    }
    function onKey(e) {
      if (e.key === "Enter") { e.preventDefault(); submit(); }
    }
    btn.addEventListener("click", submit);
    input.addEventListener("keydown", onKey);
  });
}

function ensureUsername() {
  if (userName) {
    document.getElementById("nameOverlay").classList.add("hidden");
    return Promise.resolve();
  }
  return _showNameModal("Enter your name to start");
}

function openChangeName() {
  _showNameModal("Update your name").then(() => {
    updatePlayerLabels();
  });
}

// ── App state ────────────────────────────────────────────────────────────────
let S = {
  pieces:      {},
  turn:        "white",
  status:      "playing",
  result_msg:  "",
  lastMove:    null,
  selected:    null,
  legalDests:  [],
  playerColor: "white",
  busy:        false,
};

// ── Coordinate helpers — flip when playing Black ─────────────────────────────
function sqToRowCol(sq) {
  if (S.playerColor === "black") {
    return { row: Math.floor(sq / 8), col: sq % 8 };
  }
  return { row: 7 - Math.floor(sq / 8), col: sq % 8 };
}

function rowColToSq(row, col) {
  if (S.playerColor === "black") {
    return row * 8 + col;
  }
  return (7 - row) * 8 + col;
}

// ── Build board squares ──────────────────────────────────────────────────────
function buildBoard() {
  boardEl.innerHTML = "";

  // Rank labels
  rankLabels.innerHTML = "";
  const ranks = S.playerColor === "black"
    ? [1, 2, 3, 4, 5, 6, 7, 8]
    : [8, 7, 6, 5, 4, 3, 2, 1];
  for (const r of ranks) {
    const s = document.createElement("span");
    s.textContent = r;
    rankLabels.appendChild(s);
  }

  // File labels
  fileLabels.innerHTML = "";
  const files = S.playerColor === "black"
    ? ["h", "g", "f", "e", "d", "c", "b", "a"]
    : ["a", "b", "c", "d", "e", "f", "g", "h"];
  for (const f of files) {
    const s = document.createElement("span");
    s.textContent = f;
    fileLabels.appendChild(s);
  }

  // Squares
  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const sq  = rowColToSq(row, col);
      const div = document.createElement("div");
      div.className = `sq ${(row + col) % 2 === 0 ? "light" : "dark"}`;
      div.dataset.sq = sq;
      div.addEventListener("click", onSqClick);
      boardEl.appendChild(div);
    }
  }
}

// ── Render current state onto board ─────────────────────────────────────────
function renderBoard(opts = {}) {
  const { animateSq = null } = opts;

  document.querySelectorAll(".sq").forEach(el => {
    el.innerHTML = "";
    el.classList.remove(
      "selected", "last-from", "last-to",
      "in-check", "legal-empty", "legal-capture"
    );
  });

  if (S.lastMove) {
    getSqEl(S.lastMove.from)?.classList.add("last-from");
    getSqEl(S.lastMove.to)?.classList.add("last-to");
  }

  if (S.status === "check" || S.status === "checkmate") {
    for (const [sqStr, p] of Object.entries(S.pieces)) {
      if (p.color === S.turn && p.type === 6) {
        getSqEl(+sqStr)?.classList.add("in-check");
      }
    }
  }

  for (const [sqStr, p] of Object.entries(S.pieces)) {
    const el = getSqEl(+sqStr);
    if (!el) continue;
    const span = document.createElement("span");
    span.className = "piece";
    span.innerHTML = pieceSVG(p.type, p.color);
    if (+sqStr === animateSq) span.classList.add("piece-new");
    el.appendChild(span);
  }

  if (S.selected !== null) {
    getSqEl(S.selected)?.classList.add("selected");
  }

  for (const dest of S.legalDests) {
    const el = getSqEl(dest);
    if (!el) continue;
    const hasEnemy = S.pieces[dest] && S.pieces[dest].color !== S.playerColor;
    el.classList.add(hasEnemy ? "legal-capture" : "legal-empty");
  }
}

// ── Player label / button helpers ────────────────────────────────────────────
function updatePlayerLabels() {
  nameWhite.classList.remove("editable-name");
  nameBlack.classList.remove("editable-name");
  if (S.playerColor === "white") {
    nameWhite.textContent = userName + " — White";
    nameBlack.textContent = "Bot — Black";
    nameWhite.classList.add("editable-name");
  } else {
    nameWhite.textContent = "Bot — White";
    nameBlack.textContent = userName + " — Black";
    nameBlack.classList.add("editable-name");
  }
}

document.addEventListener("click", (e) => {
  if (e.target.classList.contains("editable-name")) {
    openChangeName();
  }
});

function updateColorButtons() {
  btnPlayWhite.classList.toggle("active", S.playerColor === "white");
  btnPlayBlack.classList.toggle("active", S.playerColor === "black");
}

function getTurnSub() {
  return S.playerColor === "white" ? turnSubWhite : turnSubBlack;
}

// ── Update sidebars ──────────────────────────────────────────────────────────
function updateSidebars(st) {
  const myTurn = st.turn === S.playerColor;
  playerWhite.classList.toggle("active", st.turn === "white" && !isOver(st.status));
  playerBlack.classList.toggle("active", st.turn === "black" && !isOver(st.status));

  // Clear both turn subs, set the human one if it's their turn
  turnSubWhite.textContent = "";
  turnSubBlack.textContent = "";
  if (myTurn && !isOver(st.status)) {
    getTurnSub().textContent = "Your turn";
  }

  const score = st.eval_score ?? 0;
  const clamped = Math.max(-1000, Math.min(1000, score));
  const whitePct = ((clamped + 1000) / 2000 * 100).toFixed(1);
  evalWhiteFill.style.width = whitePct + "%";
  evalBlackFill.style.width = (100 - whitePct) + "%";
  evalScore.textContent = st.eval_label || "0.0";

  const wCap = st.white_captured || [];
  const bCap = st.black_captured || [];
  whiteCap.innerHTML = wCap.length
    ? wCap.map(s => CAP_TYPE[s] ? capPieceSVG(CAP_TYPE[s], 'white') : '').join('')
    : '<span class="material-dash">—</span>';
  blackCap.innerHTML = bCap.length
    ? bCap.map(s => CAP_TYPE[s] ? capPieceSVG(CAP_TYPE[s], 'black') : '').join('')
    : '<span class="material-dash">—</span>';

  if (st.status === "checkmate" && st.winner_color) {
    const winnerName = st.winner_color === S.playerColor ? userName : "Hannibal Bot";
    const winnerSide = st.winner_color === "white" ? "(White)" : "(Black)";
    statusMsg.textContent = "Checkmate — " + winnerName + " " + winnerSide + " wins!";
  } else {
    statusMsg.textContent = st.result_msg || "";
  }
  statusMsg.className   = "status-msg" + (st.status === "checkmate" || st.status === "draw" ? " danger" : "");

  if (st.pgn && isOver(st.status)) {
    pgnArea.classList.add("visible");
    pgnText.textContent = st.pgn;
  } else {
    pgnArea.classList.remove("visible");
    pgnText.textContent = "";
  }

  const hist = st.history || [];
  historyBody.innerHTML = "";
  for (let i = 0; i < hist.length; i += 2) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${Math.floor(i/2)+1}.</td><td>${hist[i] || ""}</td><td>${hist[i+1] || ""}</td>`;
    historyBody.appendChild(tr);
  }
  const hs = historyBody.closest(".history-scroll");
  if (hs) hs.scrollTop = hs.scrollHeight;
}

function isOver(status) {
  return status === "checkmate" || status === "draw";
}

function getSqEl(sq) {
  return boardEl.querySelector(`[data-sq="${sq}"]`);
}

// ── Apply a full server state ────────────────────────────────────────────────
function applyState(st, opts = {}) {
  S.pieces     = st.pieces    || {};
  S.turn       = st.turn;
  S.status     = st.status;
  S.result_msg = st.result_msg;
  S.lastMove   = st.last_move;
  S.selected   = null;
  S.legalDests = [];

  renderBoard(opts);
  updateSidebars(st);
}

// ── Optimistic (immediate) human move on board ───────────────────────────────
function applyLocalMove(fromSq, toSq, promoPiece) {
  const piece = S.pieces[fromSq];
  if (!piece) return false;

  const wasCapture = !!S.pieces[toSq];

  delete S.pieces[toSq];
  S.pieces[toSq] = { ...piece };
  if (promoPiece) {
    S.pieces[toSq].type   = { q:5, r:4, b:3, n:2 }[promoPiece] ?? 5;
    S.pieces[toSq].symbol = piece.color === "white"
      ? promoPiece.toUpperCase()
      : promoPiece.toLowerCase();
  }
  delete S.pieces[fromSq];

  // Handle castling rook move locally
  if (piece.type === 6 && Math.abs((fromSq % 8) - (toSq % 8)) === 2) {
    const rookFrom = toSq > fromSq ? fromSq + 3 : fromSq - 4;
    const rookTo   = toSq > fromSq ? fromSq + 1 : fromSq - 1;
    const rook = S.pieces[rookFrom];
    if (rook) {
      delete S.pieces[rookFrom];
      S.pieces[rookTo] = rook;
    }
  }

  S.lastMove   = { from: fromSq, to: toSq };
  S.selected   = null;
  S.legalDests = [];
  S.turn = S.turn === "white" ? "black" : "white";
  S.status = "playing";

  renderBoard({ animateSq: toSq });
  return wasCapture;
}

// ── Fetch legal moves from server ────────────────────────────────────────────
async function fetchLegal(sq) {
  const res  = await fetch(`/api/legal_moves?square=${sq}`);
  const data = await res.json();
  return data.ok ? data.destinations : [];
}

// ── Submit move to server ────────────────────────────────────────────────────
async function submitMove(fromSq, toSq, promo = null) {
  S.busy = true;
  setThinking(true);

  try {
    const res  = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from: fromSq, to: toSq, promotion: promo, name: userName }),
    });
    const data = await res.json();

    if (!data.ok) {
      showToast(data.error || "Illegal move");
      const fresh = await fetch("/api/state");
      const fd    = await fresh.json();
      if (fd.ok) {
        if (fd.player_color) S.playerColor = fd.player_color;
        applyState(fd.state);
      }
      return;
    }

    if (data.human_check) {
      S.status = "check";
      renderBoard();
      audio.check();
    }

    if (data.ai_move) {
      await delay(120);
      applyState(data.state, { animateSq: uciToSq(data.ai_move).to });
      playSoundForMove(data.ai_capture, data.ai_check, data.state.status, true);
    } else {
      applyState(data.state);
      if (isOver(data.state.status)) audio.gameEnd();
    }

  } catch (e) {
    showToast("Network error — is the server running?");
    console.error(e);
  } finally {
    S.busy = false;
    setThinking(false);
  }
}

function playSoundForMove(isCapture, isCheck, status, isAI) {
  if (status === "checkmate") { audio.gameEnd(); return; }
  if (isCheck)   { audio.check();   return; }
  if (isCapture) { audio.capture(); return; }
  audio.move();
}

function uciToSq(uci) {
  const files = { a:0, b:1, c:2, d:3, e:4, f:5, g:6, h:7 };
  const from  = (parseInt(uci[1]) - 1) * 8 + files[uci[0]];
  const to    = (parseInt(uci[3]) - 1) * 8 + files[uci[2]];
  return { from, to };
}

// ── Thinking indicator — targets whichever card is the AI ────────────────────
function setThinking(on) {
  const aiDots   = S.playerColor === "white" ? thinkingDotsB : thinkingDotsW;
  const humDots  = S.playerColor === "white" ? thinkingDotsW : thinkingDotsB;
  aiDots.classList.toggle("active", on);
  humDots.classList.remove("active");

  // Clear turn text while thinking
  turnSubWhite.textContent = "";
  turnSubBlack.textContent = "";
}

// ── Promotion modal ──────────────────────────────────────────────────────────
function openPromo(fromSq, toSq) {
  const opts = [
    { sym:"q", type:5 },
    { sym:"r", type:4 },
    { sym:"b", type:3 },
    { sym:"n", type:2 },
  ];
  promoOptions.innerHTML = "";
  for (const o of opts) {
    const btn = document.createElement("button");
    btn.className = "promo-btn";
    btn.innerHTML = pieceSVG(o.type, S.playerColor);
      btn.addEventListener("click", () => {
        promoOverlay.classList.remove("open");
        const wasCapture = applyLocalMove(fromSq, toSq, o.sym);
        if (wasCapture) audio.capture(); else audio.move();
        submitMove(fromSq, toSq, o.sym);
      });
    promoOptions.appendChild(btn);
  }
  promoOverlay.classList.add("open");
}

function isPromotion(fromSq, toSq) {
  const p = S.pieces[fromSq];
  if (!p || p.type !== 1) return false;
  const rank = Math.floor(toSq / 8); // python-chess rank: 0=rank1, 7=rank8
  return (p.color === "white" && rank === 7) || (p.color === "black" && rank === 0);
}

// ── Square click ─────────────────────────────────────────────────────────────
async function onSqClick(e) {
  if (S.busy) return;
  if (isOver(S.status)) return;
  if (S.turn !== S.playerColor) return;

  const sq    = parseInt(e.currentTarget.dataset.sq);
  const piece = S.pieces[sq];

  if (S.selected !== null) {
    if (sq === S.selected) {
      S.selected = null; S.legalDests = [];
      renderBoard();
      return;
    }

    if (S.legalDests.includes(sq)) {
      const from = S.selected;
      if (isPromotion(from, sq)) {
        S.selected = null; S.legalDests = [];
        openPromo(from, sq);
      } else {
        const wasCapture = applyLocalMove(from, sq, null);
        if (wasCapture) audio.capture(); else audio.move();
        submitMove(from, sq);
      }
      return;
    }

    if (piece && piece.color === S.playerColor) {
      S.selected  = sq;
      S.legalDests = await fetchLegal(sq);
      renderBoard();
      return;
    }

    S.selected = null; S.legalDests = [];
    renderBoard();
    return;
  }

  if (piece && piece.color === S.playerColor) {
    S.selected  = sq;
    S.legalDests = await fetchLegal(sq);
    renderBoard();
  }
}

// ── Start new game with color selection ──────────────────────────────────────
async function startNewGame(color) {
  if (S.busy) return;
  S.busy = true;
  btnPlayWhite.disabled = true;
  btnPlayBlack.disabled = true;

  // Show thinking while AI computes first move (only when player is black)
  if (color === "black") {
    S.playerColor = "black";
    updatePlayerLabels();
    updateColorButtons();
    buildBoard();
    setThinking(true);
  }

  try {
    const res  = await fetch("/api/new_game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color, name: userName }),
    });
    const data = await res.json();

    if (data.ok) {
      S.playerColor = data.player_color;
      updatePlayerLabels();
      updateColorButtons();
      buildBoard();

      if (data.ai_move) {
        // AI made first move (player chose black)
        setThinking(false);
        applyState(data.state, { animateSq: uciToSq(data.ai_move).to });
        playSoundForMove(data.ai_capture, data.ai_check, data.state.status, true);
      } else {
        setThinking(false);
        applyState(data.state);
      }
      audio.move();
    }
  } catch (e) {
    setThinking(false);
    showToast("Could not start new game.");
    console.error(e);
  } finally {
    S.busy = false;
    btnPlayWhite.disabled = false;
    btnPlayBlack.disabled = false;
  }
}

function showConfirmPopup(color) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("confirmOverlay");
    const title   = document.getElementById("confirmTitle");
    const yesBtn  = document.getElementById("confirmYes");
    const noBtn   = document.getElementById("confirmNo");

    const label = color === "white" ? "White" : "Black";
    title.textContent = "Start new game as " + label + "?";
    overlay.classList.add("open");

    function cleanup() {
      overlay.classList.remove("open");
      yesBtn.removeEventListener("click", onYes);
      noBtn.removeEventListener("click", onNo);
    }
    function onYes()  { cleanup(); resolve(true); }
    function onNo()   { cleanup(); resolve(false); }

    yesBtn.addEventListener("click", onYes);
    noBtn.addEventListener("click", onNo);
  });
}

btnPlayWhite.addEventListener("click", () => {
  showConfirmPopup("white").then(ok => { if (ok) startNewGame("white"); });
});
btnPlayBlack.addEventListener("click", () => {
  showConfirmPopup("black").then(ok => { if (ok) startNewGame("black"); });
});

// ── Toast ────────────────────────────────────────────────────────────────────
let toastEl = null;
function showToast(msg) {
  if (!toastEl) {
    toastEl = document.createElement("div");
    toastEl.className = "toast";
    document.body.appendChild(toastEl);
  }
  toastEl.textContent = msg;
  toastEl.classList.add("visible");
  setTimeout(() => toastEl.classList.remove("visible"), 2800);
}

// ── Utility ──────────────────────────────────────────────────────────────────
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  await ensureUsername();
  buildBoard();
  try {
    const res  = await fetch("/api/state");
    const data = await res.json();
    if (data.ok) {
      S.playerColor = data.player_color || "white";
      updatePlayerLabels();
      updateColorButtons();
      buildBoard();
      applyState(data.state);
    }
  } catch {
    showToast("Cannot reach server — make sure app.py is running.");
  }
}

init();