(() => {
"use strict";
const $ = id => document.getElementById(id);
let chosen = null, guessed = new Set(), timer = null, searchSeq = 0;
const hide = (id, yes=true) => $(id).classList.toggle("gp-hidden", yes);
const error = msg => { $("gp-error").textContent = msg || ""; hide("gp-error", !msg); };
async function api(url, options) {
  const response = await fetch(url, {credentials:"same-origin", ...options});
  const type = response.headers.get("content-type") || "";
  if (!type.includes("application/json")) throw Error(response.status === 401 ? "Please log in to play." : "Server returned an unexpected response.");
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "Request failed.");
  return data;
}
const post = (path, data={}) => api(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const imageHTML = (url, name) => url ? `<img src="${escapeHTML(url)}" alt="${escapeHTML(name)}" onerror="this.style.display='none'">` : "";
function stats(s={}) {
  $("gp-wins").textContent = s.wins ?? 0;
  $("gp-win-rate").textContent = `${s.win_rate ?? 0}%`;
  $("gp-streak").textContent = s.current_streak ?? 0;
  $("gp-best").textContent = s.best_streak ?? 0;
}
function renderGuess(p) {
  const labels={team:"TEAM",position:"POSITION",nationality:"NATIONALITY",rating:"RATING",offense:"OFFENSE",defense:"DEFENSE"};
  const cells=Object.entries(labels).map(([key,label])=>{
    const state=p.matches[key] || {};
    const arrow=state.direction==="up"?" ↑":state.direction==="down"?" ↓":"";
    return `<div class="gp-attribute ${state.match?"match":""}"><small>${label}</small><strong>${escapeHTML(p[key])}${arrow}</strong></div>`;
  }).join("");
  const card=document.createElement("article");
  card.className="gp-guess";
  card.innerHTML=`<div class="gp-guess-top">${imageHTML(p.picture_url,p.name)}<div><strong>${escapeHTML(p.name)}</strong><small>${p.correct?"CORRECT PLAYER":"YOUR GUESS"}</small></div></div><div class="gp-attributes">${cells}</div>`;
  $("gp-history").prepend(card);
  guessed.add(p.id);
}
function resetUI() {
  chosen=null;guessed=new Set();$("gp-search").value="";$("gp-selected-label").textContent="Select a player from the results.";
  $("gp-submit").disabled=true;$("gp-history").innerHTML="";$("gp-suggestions").innerHTML="";
  hide("gp-suggestions");hide("gp-finish");hide("gp-intro");hide("gp-play",false);error("");
  $("gp-attempt").textContent="1";$("gp-remaining").textContent="8 remaining";
}
function finish(data) {
  hide("gp-play");hide("gp-finish",false);
  $("gp-finish-title").textContent=data.won?"YOU GOT IT!":"GAME OVER";
  $("gp-finish-message").textContent=data.won?`You found the player in ${data.guesses_used ?? data.guesses.length} guesses!`:"You used all eight guesses.";
  const p=data.answer;
  $("gp-answer").innerHTML=p?`${imageHTML(p.picture_url,p.name)}${escapeHTML(p.name)}<div style="font-size:13px;color:#aaa6a3">${escapeHTML(p.team)}</div>`:"";
  $("gp-unlocks").textContent=(data.new_achievements||[]).map(a=>`🏆 ${a.name}`).join(" · ");
}
async function start() {
  error("");
  try {const data=await post("/api/games/guess-the-player/start");resetUI();stats(data.stats);}
  catch(e){error(e.message);}
}
async function lookup() {
  const q=$("gp-search").value.trim(), seq=++searchSeq;
  chosen=null;$("gp-submit").disabled=true;
  $("gp-selected-label").textContent="Select a player from the results.";
  if(!q){hide("gp-suggestions");return;}
  try {
    const data=await api(`/api/games/guess-the-player/players?q=${encodeURIComponent(q)}`);
    if(seq!==searchSeq)return;
    const list=$("gp-suggestions");list.innerHTML="";
    for(const p of data.players.filter(p=>!guessed.has(p.id))) {
      const btn=document.createElement("button");btn.type="button";btn.className="gp-option";btn.setAttribute("role","option");
      btn.innerHTML=`${imageHTML(p.picture_url,p.name)}<span><strong>${escapeHTML(p.name)}</strong><small>${escapeHTML(p.team)} · ${escapeHTML(p.position)}</small></span>`;
      btn.addEventListener("click",()=>{chosen=p;$("gp-search").value=p.name;$("gp-selected-label").textContent=`Selected: ${p.name} (${p.team})`;$("gp-submit").disabled=false;hide("gp-suggestions");});
      list.appendChild(btn);
    }
    if(!list.children.length)list.innerHTML='<div style="padding:16px;color:#aaa6a3">No available players found.</div>';
    hide("gp-suggestions",false);
  } catch(e){error(e.message);}
}
async function guess() {
  if(!chosen)return;
  $("gp-submit").disabled=true;error("");
  try {
    const data=await post("/api/games/guess-the-player/guess",{player_id:chosen.id});
    renderGuess(data.guess);stats(data.stats);
    $("gp-attempt").textContent=Math.min(8,data.guesses_used+1);
    $("gp-remaining").textContent=`${data.remaining} remaining`;
    chosen=null;$("gp-search").value="";$("gp-selected-label").textContent="Select a player from the results.";
    if(data.game_over)finish(data);
  }catch(e){error(e.message);$("gp-submit").disabled=!chosen;}
}
async function restore() {
  try {
    const data=await api("/api/games/guess-the-player/state");stats(data.stats);
    if(!data.active && !data.guesses.length)return;
    resetUI();
    for(const p of data.guesses)renderGuess(p);
    $("gp-attempt").textContent=Math.min(8,data.guesses.length+1);
    $("gp-remaining").textContent=`${data.remaining} remaining`;
    if(!data.active)finish({...data,guesses_used:data.guesses.length});
  } catch(e){if(!/log in/i.test(e.message))error(e.message);}
}
$("gp-start").addEventListener("click",start);
$("gp-again").addEventListener("click",start);
$("gp-submit").addEventListener("click",guess);
$("gp-search").addEventListener("input",()=>{clearTimeout(timer);timer=setTimeout(lookup,180);});
$("gp-search").addEventListener("keydown",e=>{if(e.key==="Escape")hide("gp-suggestions");});
document.addEventListener("click",e=>{if(!e.target.closest(".gp-search-wrap"))hide("gp-suggestions");});
restore();
})();
