const $ = id => document.getElementById(id);
let user = 'alice', generation = 0, busy = false;
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; };
function badge(text) { return node('span', text, 'badge ' + text); }
function details(title, value) { const d = node('details'); d.append(node('summary',title),node('pre',typeof value==='string'?value:JSON.stringify(value,null,2))); return d; }
function connection(ok) { $('connection').textContent = ok ? '● FalkorDB 연결됨' : '● FalkorDB 연결 장애'; $('connection').classList.toggle('offline', !ok); }
async function api(path, body) {
  let res;
  try { res=await fetch(path, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  catch(e){ connection(false); throw Error('서버에 연결할 수 없습니다. 표시된 데이터는 이전 조회 결과입니다.'); }
  const data=await res.json();
  if(!res.ok){ if(res.status===503) connection(false); throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)); }
  return data;
}
function error(e) { $('error').hidden=false; $('error').textContent=e.message; }
async function action(fn) { if(busy)return;busy=true;$('error').hidden=true;document.querySelectorAll('button,select').forEach(n=>n.disabled=true);try{await fn();}catch(e){error(e);}finally{busy=false;document.querySelectorAll('button,select').forEach(n=>n.disabled=n.dataset.terminal==='true');} }
function render(data) {
  $('count').textContent = data.memories.length+' MEMORIES';
  for(const id of ['memories','history','tasks','results']) $(id).replaceChildren();
  for(const m of [...data.memories].sort((a,b)=>({semantic:0,procedural:1,episodic:2}[a.kind]-{semantic:0,procedural:1,episodic:2}[b.kind])||b.created_at-a.created_at)) {
    const card=node('div',undefined,'memory'), tags=node('div',undefined,'badges');tags.append(badge(m.kind),badge(m.status));
    card.append(tags,node('p',m.content),node('div',m.id,'id'),details('원본 메시지 · SUPPORTS',m.sources),details('유효 시각 · 구조화된 속성',m));$('memories').append(card);
  }
  for(const h of data.history){ const card=node('div',undefined,'history-item');card.append(node('p',h.before,'before'),node('div','↑ SUPERSEDES','id'),node('p',h.after),details('변경 근거와 ID',h));$('history').append(card); }
  for(const t of data.tasks){const card=node('div',undefined,'task');card.append(badge(t.status),node('p',t.prompt),node('div',`${t.from_agent} → ${t.to_agent} · v${t.version} · attempts ${t.attempts}`,'route'),node('div',t.id,'id'),details('핸드오프 상태',t)); const btn=node('button',t.status==='completed'||t.status==='failed'?'실행 종료':'Executor 실행');btn.dataset.terminal=String(t.status==='completed'||t.status==='failed');btn.disabled=btn.dataset.terminal==='true';btn.onclick=()=>action(async()=>{await api(`/api/${user}/tasks/${t.id}/execute`,{});await refresh();});card.append(btn);const ev=node('button','상태 전이');ev.className='quiet';ev.onclick=()=>action(async()=>{card.append(details('그래프에 기록된 전이',[...(t.events||[])].sort((a,b)=>a.version-b.version)));});card.append(ev);$('tasks').append(card);}
  for(const r of data.results){const card=node('div',undefined,'result');card.append(badge(r.status),node('pre',r.content),details('Task → Result → Memory ← Message',r.evidence));$('results').append(card);}
  for(const id of ['memories','history','tasks','results']) if(!$(id).children.length) $(id).append(node('p','아직 기록이 없습니다.'));
}
async function refresh(){const current=++generation, selected=user;const health=await api('/api/health');connection(true);$('mode').textContent=health.llm_mode.toUpperCase();const data=await api(`/api/${selected}/snapshot`);if(current===generation&&selected===user)render(data);}
function bubble(role,text){const n=node('div',undefined,'bubble '+role);n.append(node('strong',role),node('span',text));$('chat').append(n);$('chat').scrollTop=$('chat').scrollHeight;return n;}
$('form').onsubmit=e=>{e.preventDefault();action(async()=>{const text=$('message').value.trim();if(!text)return;bubble('user',text);$('message').value='';const r=await api('/api/chat',{user,text});const n=bubble('coordinator',r.answer);n.append(details('이 응답이 사용한 기억',r.evidence));await refresh();});};
$('user').onchange=()=>action(async()=>{user=$('user').value;generation++;$('chat').replaceChildren();for(const id of ['memories','history','tasks','results'])$(id).replaceChildren();await refresh();});
$('refresh').onclick=()=>action(refresh);
$('resume').onclick=()=>action(async()=>{await api(`/api/${user}/resume`,{});await refresh();});
document.querySelectorAll('[data-text]').forEach(b=>b.onclick=()=>{$('message').value=b.dataset.text;$('message').focus();});
$('demo').onclick=()=>action(async()=>{bubble('system','5개 장면을 실제 FalkorDB에서 실행 중입니다…');const data=await api('/api/demo',{});$('demo-panel').hidden=false;$('demo-scenes').replaceChildren();for(const s of data.transcript){const n=node('div',undefined,'scene');n.append(node('h3',s.scene),node('p',s.input||s.scope||'Bob: empty graph → Go'),node('p',s.response?.answer||''));if(s.execution)n.append(node('pre',s.execution.result?.content||''));if(s.empty_bob)n.append(node('p','Before Bob writes: '+s.empty_bob.answer));$('demo-scenes').append(n);}render(data.alice);bubble('system','데모 완료. 아래 패널은 격리된 Alice 데모 그래프입니다. 새로고침하면 선택된 사용자 그래프로 돌아갑니다.');$('count').textContent+=' · DEMO';$('demo-scenes').append(details('전체 검증 데이터 · '+data.graph_prefix,data));});
action(refresh);
setInterval(async()=>{if(busy)return;try{await api('/api/health');connection(true);}catch(e){connection(false);error(e);}},15000);
