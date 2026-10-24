'use strict';
const $ = id => document.getElementById(id);
let board = null;
let selected = null;
let timer = null;
let submitting = false;
const api = async (url, options = {}) => {
  const response = await fetch(url, {credentials:'same-origin', ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
};
function message(text) { $('status').textContent = text; }
function showStats(s = {}) {
  const items = [['Games',s.games],['Wins',s.wins],['Losses',s.losses],['Best Filled',`${s.best_correct || 0}/9`],['Win Rate',`${s.win_rate || 0}%`]];
  $('stats').replaceChildren(...items.map(([label,value]) => {
    const div=document.createElement('div'); div.className='stat';
    const strong=document.createElement('strong'); strong.textContent=value ?? 0;
    const small=document.createElement('small'); small.textContent=label;
    div.append(strong,small); return div;
  }));
}
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
    // Prefer the site's existing country aliases and FlagCDN SVG images.
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
      img.onerror = () => { img.remove(); };
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
function updateButtons(){
  $('new-game').disabled=!!board && !board.finished;
  $('give-up').disabled=!board || board.finished;
  const left=board ? Math.max(0,(board.max_mistakes||3)-(board.mistakes||0)) : 3;
  $('lives').textContent='♥ '.repeat(left)+'♡ '.repeat(3-left);
  $('lives').setAttribute('aria-label',`${left} lives remaining`);
}
function render() {
  const container=$('board'); container.replaceChildren();
  if (!board) {message('No grid yet. Click NEW GRID to begin.');updateButtons();return;}
  const corner=document.createElement('div'); corner.className='corner'; container.append(corner);
  for(const cat of board.columns) container.append(categoryElement(cat,'top'));
  for(let r=0;r<3;r++){
    container.append(categoryElement(board.rows[r],'side'));
    for(let c=0;c<3;c++){
      const i=r*3+c, cell=board.cells[i];
      const el=document.createElement('button');el.type='button';el.className=`cell ${cell?'filled':'available'} ${selected===i?'selected':''}`;
      if(cell) {
        if(cell.picture_url){
          const img=document.createElement('img');img.src=cell.picture_url;img.alt=cell.name;
          img.className='player-photo';img.loading='lazy';
          img.onerror=()=>img.remove();el.append(img);
        }
        const name=document.createElement('span');name.className='player-name';name.textContent=cell.name;el.append(name);
      } else el.textContent='+ SELECT PLAYER';
      el.disabled=!!cell || board.finished;
      el.addEventListener('click',()=>selectCell(i));container.append(el);
    }
  }
  const filled=board.cells.filter(Boolean).length;
  message(board.finished ? (board.won?'🏆 Perfect grid! You won.':board.gave_up?'You gave up. Start a new grid.':'Game over. You ran out of lives.') : `${filled}/9 correct · ${board.max_mistakes-board.mistakes} lives remaining`);
  updateButtons();
}
function selectCell(index){selected=index;$('search-panel').hidden=false;$('selection-label').textContent=`${board.rows[Math.floor(index/3)].label} · ${board.columns[index%3].label}`;$('player-search').value='';$('results').replaceChildren();$('player-search').focus();render();}
function closeSearch(){selected=null;$('search-panel').hidden=true;render();}
async function searchPlayers(){const query=$('player-search').value.trim();const results=$('results');results.replaceChildren();if(query.length<2)return;
  try{const data=await api(`/api/games/basketball-grid/players?q=${encodeURIComponent(query)}`);if(query!==$('player-search').value.trim())return;
    for(const p of data.players){const b=document.createElement('button');b.type='button';b.className='result';const name=document.createElement('span');name.textContent=p.name;const detail=document.createElement('small');detail.textContent=`${p.team} · ${p.position}`;b.append(name,detail);b.addEventListener('click',()=>submitGuess(p.id));results.append(b);}
    if(!data.players.length)results.textContent='No players found.';
  }catch(err){results.textContent=err.message;}
}
async function submitGuess(playerId){if(selected===null||submitting)return;const index=selected;submitting=true;
  try{const data=await api('/api/games/basketball-grid/guess',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index,player_id:playerId})});board=data.board;showStats(data.stats);closeSearch();if(!data.correct)message(`Incorrect player. ${board.mistakes}/${board.max_mistakes} mistakes.`);}
  catch(err){message(err.message);}finally{submitting=false;}
}
async function newGame(){try{const data=await api('/api/games/basketball-grid/start',{method:'POST'});board=data.board;showStats(data.stats);closeSearch();}catch(err){message(err.message);}}
async function giveUp(){
  if(!board || board.finished)return;
  if(!confirm('Give up this grid? It will count as a loss.'))return;
  try{
    const data=await api('/api/games/basketball-grid/give-up',{method:'POST'});
    board=data.board;showStats(data.stats);closeSearch();
  }catch(err){message(err.message);}
}
async function init(){try{const data=await api('/api/games/basketball-grid/state');board=data.board;showStats(data.stats);render();}catch(err){message(err.message);}}
$('new-game').addEventListener('click',newGame);$('give-up').addEventListener('click',giveUp);$('cancel').addEventListener('click',closeSearch);$('player-search').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(searchPlayers,220);});init();
