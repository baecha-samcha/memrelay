const $ = id => document.getElementById(id);
let user = 'alice', generation = 0, busy = false;
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; };
function badge(text) { return node('span', text, 'badge ' + text); }
function details(title, value) { const d = node('details'); d.append(node('summary',title),node('pre',typeof value==='string'?value:JSON.stringify(value,null,2))); return d; }
function connection(ok) { $('connection').textContent = ok ? '● FalkorDB connected' : '● FalkorDB disconnected'; $('connection').classList.toggle('online', ok); $('connection').classList.toggle('offline', !ok); }
async function api(path, body) {
  let res;
  try { res=await fetch(path, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  catch(e){ connection(false); throw Error('Cannot reach the server. Displayed data may be from an earlier request.'); }
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
    card.append(tags,node('p',m.content),node('div',m.id,'id'),details('Source messages · SUPPORTS',m.sources),details('Validity & structured properties',m));$('memories').append(card);
  }
  for(const h of data.history){ const card=node('div',undefined,'history-item');card.append(node('p',h.before,'before'),node('div','↑ SUPERSEDES','id'),node('p',h.after),details('Revision evidence & IDs',h));$('history').append(card); }
  for(const t of data.tasks){const card=node('div',undefined,'task');card.append(badge(t.status),node('p',t.prompt),node('div',`${t.from_agent} → ${t.to_agent} · v${t.version} · attempts ${t.attempts}`,'route'),node('div',t.id,'id'),details('Handoff details',t)); const btn=node('button',t.status==='completed'||t.status==='failed'?'Execution finished':'Run Executor');btn.dataset.terminal=String(t.status==='completed'||t.status==='failed');btn.disabled=btn.dataset.terminal==='true';btn.onclick=()=>action(async()=>{await api(`/api/${user}/tasks/${t.id}/execute`,{});await refresh();});card.append(btn);const ev=node('button','State transitions');ev.className='quiet';ev.onclick=()=>action(async()=>{card.append(details('Transitions recorded in the graph',[...(t.events||[])].sort((a,b)=>a.version-b.version)));});card.append(ev);$('tasks').append(card);}
  for(const r of data.results){const card=node('div',undefined,'result');card.append(badge(r.status),node('pre',r.content),details('Task → Result → Memory ← Message',r.evidence));$('results').append(card);}
  for(const id of ['memories','history','tasks','results']) if(!$(id).children.length) $(id).append(node('p','No records yet.'));
}
async function refresh(){const current=++generation, selected=user;const health=await api('/api/health');connection(true);$('mode').textContent=health.llm_mode.toUpperCase();const data=await api(`/api/${selected}/snapshot`);if(current===generation&&selected===user)render(data);}
function bubble(role,text){const n=node('div',undefined,'bubble '+role);n.append(node('strong',role),node('span',text));$('chat').append(n);$('chat').scrollTop=$('chat').scrollHeight;return n;}
$('form').onsubmit=e=>{e.preventDefault();action(async()=>{const text=$('message').value.trim();if(!text)return;bubble('user',text);$('message').value='';const r=await api('/api/chat',{user,text});const n=bubble('coordinator',r.answer);n.append(details('Memories used in this response',r.evidence));await refresh();});};
$('user').onchange=()=>action(async()=>{user=$('user').value;generation++;$('chat').replaceChildren();for(const id of ['memories','history','tasks','results'])$(id).replaceChildren();await refresh();});
$('refresh').onclick=()=>action(refresh);
$('resume').onclick=()=>action(async()=>{await api(`/api/${user}/resume`,{});await refresh();});
document.querySelectorAll('[data-text]').forEach(b=>b.onclick=()=>{$('message').value=b.dataset.text;$('message').focus();});
$('demo').onclick=()=>action(async()=>{bubble('system','Running five scenes against real FalkorDB…');const data=await api('/api/demo',{});$('demo-panel').hidden=false;$('demo-scenes').replaceChildren();for(const s of data.transcript){const n=node('div',undefined,'scene');n.append(node('h3',s.scene),node('p',s.input||s.scope||'Bob: empty graph → Go'),node('p',s.response?.answer||''));if(s.execution)n.append(node('pre',s.execution.result?.content||''));if(s.empty_bob)n.append(node('p','Before Bob writes: '+s.empty_bob.answer));$('demo-scenes').append(n);}render(data.alice);bubble('system','Demo complete. The panels show an isolated Alice demo graph. Refresh to return to the selected user graph.');$('count').textContent+=' · DEMO';$('demo-scenes').append(details('Full demo evidence · '+data.graph_prefix,data));});
action(refresh);
setInterval(async()=>{if(busy)return;try{await api('/api/health');connection(true);}catch(e){connection(false);error(e);}},15000);
