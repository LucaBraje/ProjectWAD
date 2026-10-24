"use strict";

const $ = id => document.getElementById(id);
let board = null;
let selected = null;
let timer = null;
let submitting = false;

const api = async (url, options = {}) => {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
};

// #status is visually hidden, but remains available for accessibility/errors.
function message(text) { $('status').textContent = text; }

function categoryElement(cat, extraClass) {
  const el = document.createElement('div');
  el.className = `axis ${extraClass}`;
  el.title = cat.label;

  if (cat.type === 'team' && cat.image_url) {
    const img = document.createElement('img');
    img.className = 'team-logo';
    img.src = cat.image_url;
    img.alt = `${cat.label} logo`;
    img.loading = 'lazy';
    img.onerror = () => { img.remove(); el.textContent = cat.label; };
    el.append(img);
  } else if (cat.type === 'nationality') {
    const url = typeof getFlagUrl === 'function' ? getFlagUrl(cat.label) : null;
    const code = String(cat.flag_code || '').toLowerCase();
    const fallbackUrl = /^[a-z]{2}$/.test(code) ? `https://flagcdn.com/${code}.svg` : null;
    const imgUrl = url || fallbackUrl;
    if (imgUrl) {
      const img = document.createElement('img');
      img.className = 'country-flag';
      img.src = imgUrl;
      img.alt = `${cat.label} flag`;
      img.loading = 'lazy';
      img.onerror = () => img.remove();
      el.append(img);
    }
    const name = document.createElement('span');
    name.className = 'flag-name';
    name.textContent = cat.label;
    el.append(name);
  } else {
    el.textContent = cat.label;
  }
  return el;
}

function updateButtons() {
  $('new-game').disabled = !!board && !board.finished;
  $('give-up').disabled = !board || board.finished;
  const max = board ? (board.max_mistakes ?? 3) : 3;
  const left = board ? Math.max(0, max - (board.mistakes ?? 0)) : max;
  $('lives').textContent = '♥ '.repeat(left) + '♡ '.repeat(Math.max(0, max - left));
  $('lives').setAttribute('aria-label', `${left} lives remaining`);
}

// Directly update the scoreboard from game state (no MutationObserver needed).
function updateScore() {
  const filled = board ? board.cells.filter(Boolean).length : 0;
  $('correct-count').textContent = `${filled}/9`;
}

function updateGameResult() {
  const result = $('game-result');
  if (!board || !board.finished) {
    result.hidden = true;
    result.classList.remove('win', 'lose');
    return;
  }
  const filled = board.cells.filter(Boolean).length;
  result.hidden = false;
  result.classList.toggle('win', !!board.won);
  result.classList.toggle('lose', !board.won);

  if (board.won) {
    $('game-result-title').textContent = '🏆 YOU WON!';
    $('game-result-description').textContent = 'Perfect grid! You correctly filled all 9 squares.';
  } else if (board.gave_up) {
    $('game-result-title').textContent = 'YOU GAVE UP';
    $('game-result-description').textContent = `You completed ${filled}/9 squares. Try another grid!`;
  } else {
    $('game-result-title').textContent = 'GAME OVER';
    $('game-result-description').textContent = `You completed ${filled}/9 squares before running out of lives.`;
  }
}

function render() {
  const container = $('board');
  container.replaceChildren();
  if (!board) {
    message('No grid yet. Click NEW GRID to begin.');
    updateScore();
    updateButtons();
    updateGameResult();
    return;
  }

  const corner = document.createElement('div');
  corner.className = 'corner';
  container.append(corner);
  for (const cat of board.columns) container.append(categoryElement(cat, 'top'));

  for (let r = 0; r < 3; r++) {
    container.append(categoryElement(board.rows[r], 'side'));
    for (let c = 0; c < 3; c++) {
      const i = r * 3 + c;
      const cell = board.cells[i];
      const el = document.createElement('button');
      el.type = 'button';
      el.className = `cell ${cell ? 'filled' : 'available'} ${selected === i ? 'selected' : ''}`;
      if (cell) {
        if (cell.picture_url) {
          const img = document.createElement('img');
          img.src = cell.picture_url;
          img.alt = cell.name;
          img.className = 'player-photo';
          img.loading = 'lazy';
          img.onerror = () => img.remove();
          el.append(img);
        }
        const name = document.createElement('span');
        name.className = 'player-name';
        name.textContent = cell.name;
        el.append(name);
      } else {
        el.textContent = '+ SELECT PLAYER';
      }
      el.disabled = !!cell || board.finished;
      el.addEventListener('click', () => selectCell(i));
      container.append(el);
    }
  }

  const filled = board.cells.filter(Boolean).length;
  message(board.finished
    ? (board.won ? 'Perfect grid! You won.' : board.gave_up ? 'You gave up.' : 'Game over. You ran out of lives.')
    : `${filled}/9 correct`);
  updateScore();
  updateButtons();
  updateGameResult();
}

function selectCell(index) {
  selected = index;
  $('search-panel').hidden = false;
  $('selection-label').textContent = `${board.rows[Math.floor(index / 3)].label} · ${board.columns[index % 3].label}`;
  $('player-search').value = '';
  $('results').replaceChildren();
  $('player-search').focus();
  render();
}

function closeSearch() {
  selected = null;
  $('search-panel').hidden = true;
  render();
}

async function searchPlayers() {
  const query = $('player-search').value.trim();
  const results = $('results');
  results.replaceChildren();
  if (query.length < 2) return;
  try {
    const data = await api(`/api/games/basketball-grid/players?q=${encodeURIComponent(query)}`);
    if (query !== $('player-search').value.trim()) return;
    for (const p of data.players) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'result';
      const name = document.createElement('span');
      name.textContent = p.name;
      const detail = document.createElement('small');
      detail.textContent = `${p.team} · ${p.position}`;
      b.append(name, detail);
      b.addEventListener('click', () => submitGuess(p.id));
      results.append(b);
    }
    if (!data.players.length) results.textContent = 'No players found.';
  } catch (err) { results.textContent = err.message; }
}

async function submitGuess(playerId) {
  if (selected === null || submitting) return;
  const index = selected;
  submitting = true;
  try {
    const data = await api('/api/games/basketball-grid/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ index, player_id: playerId })
    });
    board = data.board;
    closeSearch(); // Calls render(), which also displays win/loss results.
    if (!data.correct && !board.finished) {
      message(`Incorrect player. ${board.mistakes}/${board.max_mistakes} mistakes.`);
    }
  } catch (err) { message(err.message); }
  finally { submitting = false; }
}

async function newGame() {
  try {
    const data = await api('/api/games/basketball-grid/start', { method: 'POST' });
    board = data.board;
    closeSearch(); // Also hides any previous result.
  } catch (err) { message(err.message); }
}

async function giveUp() {
  if (!board || board.finished) return;
  if (!confirm('Give up this grid? It will count as a loss.')) return;
  try {
    const data = await api('/api/games/basketball-grid/give-up', { method: 'POST' });
    board = data.board;
    closeSearch();
  } catch (err) { message(err.message); }
}

async function init() {
  try {
    const data = await api('/api/games/basketball-grid/state');
    board = data.board;
    render();
  } catch (err) { message(err.message); }
}

$('new-game').addEventListener('click', newGame);
$('give-up').addEventListener('click', giveUp);
$('cancel').addEventListener('click', closeSearch);
$('player-search').addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(searchPlayers, 220);
});
init();
