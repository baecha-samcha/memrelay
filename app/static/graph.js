/* Read-only Cytoscape view. Every displayed edge is returned by FalkorDB. */
(() => {
  const el = id => document.getElementById(id);
  const make = (tag, text, className) => {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  };
  const structural = new Set(['User', 'Session', 'Entity', 'TaskEvent']);
  let cy = null, controller = null, serial = 0, payload = null;
  let selected = {user: 'alice', demoId: null}, latestDemo = null;
  let onConnection = () => {};
  const colors = {semantic:'#c99e52', procedural:'#9380b6', episodic:'#68a28b',
    Message:'#9db5c4', Agent:'#24654c', Task:'#d78b67', TaskResult:'#6483ac'};
  const short = (text, length=42) => String(text || '').length > length ? String(text).slice(0,length-1)+'…' : String(text || '');
  const props = n => n.data('properties') || {};

  function label(data) {
    const p = data.properties;
    if (data.type === 'Memory') {
      const title = data.kind === 'semantic' ? `${p.predicate}: ${p.object}` :
        data.kind === 'procedural' ? 'Summary procedure' : short(p.content, 32);
      return `${short(title)}\n${data.kind} · ${p.status}`;
    }
    if (data.type === 'Agent') return `${p.role || p.id}\nAgent`;
    if (data.type === 'Message') return `${p.role === 'assistant' ? 'Reply' : 'Message'}\n${short(p.content,32)}`;
    if (data.type === 'Task') return `Project task\n${p.status}`;
    if (data.type === 'TaskResult') return `Task result\n${p.status}`;
    if (data.type === 'TaskEvent') return `Transition: ${p.status}\nv${p.version}`;
    return `${data.type}\n${short(p.name || p.id,28)}`;
  }

  function controls(ready) {
    for (const button of document.querySelectorAll('[data-graph-control]')) {
      button.dataset.graphDisabled = String(!ready);
      button.disabled = !ready;
    }
  }

  function overlay(text, state) {
    el('graph-message').textContent = text;
    el('graph-message').hidden = !text;
    el('knowledge-panel').dataset.state = state;
  }

  function invalidate(message='Graph cleared. Refresh to load current data.', state='stale') {
    serial++;
    if (controller) controller.abort();
    controller = null;
    payload = null;
    if (cy) { cy.stop(); cy.elements().remove(); }
    el('graph-count').textContent = '0 nodes · 0 edges';
    el('graph-details').replaceChildren(make('p', 'No current graph selection.'));
    el('graph-read').textContent = state === 'loading' ? 'Querying FalkorDB…' : 'No current graph data';
    el('graph-revision-note').textContent = 'SUPERSEDES arrows point from the new memory to the previous memory.';
    overlay(message, state);
    controls(false);
  }

  function init() {
    if (cy || typeof cytoscape !== 'function') return;
    cy = cytoscape({container:el('knowledge-graph'), elements:[], pixelRatio:1,
      minZoom:.18, maxZoom:2.8, wheelSensitivity:.2, motionBlur:false,
      hideEdgesOnViewport:true, textureOnViewport:true,
      style:[
        {selector:'node',style:{'width':48,'height':48,'background-color':n => colors[n.data('kind')] || colors[n.data('type')] || '#acb8ae',
          'label':'data(label)','color':'#233b31','font-size':12,'text-wrap':'wrap','text-max-width':140,
          'text-valign':'bottom','text-margin-y':8,'border-width':2,'border-color':'#ffffff'}},
        {selector:'node[type="Message"]',style:{'shape':'round-rectangle','width':56,'height':34}},
        {selector:'node[kind="episodic"]',style:{'shape':'diamond','width':40,'height':40}},
        {selector:'node[kind="procedural"]',style:{'shape':'round-hexagon','width':58,'height':48}},
        {selector:'node[type="Agent"]',style:{'shape':'hexagon','width':60,'height':54}},
        {selector:'node[type="Task"]',style:{'shape':'rectangle','width':52,'height':40}},
        {selector:'node[type="TaskResult"]',style:{'shape':'octagon','width':54,'height':46}},
        {selector:'node.structural',style:{'width':30,'height':30,'font-size':9,'background-color':'#c4cec5'}},
        {selector:'node[status="superseded"]',style:{'border-style':'dashed','border-color':'#8a6d3b','border-width':3,'background-opacity':.55}},
        {selector:'node[status="disputed"]',style:{'border-color':'#bc5d46','border-style':'dashed'}},
        {selector:'edge',style:{'width':1.2,'line-color':'#b8c8bd','target-arrow-color':'#b8c8bd',
          'target-arrow-shape':'triangle','curve-style':'bezier','label':'data(type)','font-size':8,
          'color':'#657b6d','text-background-color':'#f7faf7','text-background-opacity':.9,
          'text-background-padding':2,'text-rotation':'autorotate','arrow-scale':.8}},
        {selector:'edge[type="SUPERSEDES"]',style:{'width':4,'line-color':'#a45178','target-arrow-color':'#a45178',
          'color':'#8a365d','font-size':12,'font-weight':'bold','arrow-scale':1.3,'z-index':20}},
        {selector:'edge[type="HANDED_OFF_TO"]',style:{'width':3,'line-color':'#236347','target-arrow-color':'#236347','color':'#236347','font-size':11}},
        {selector:'edge[type="USES_MEMORY"]',style:{'line-color':'#829cb9','target-arrow-color':'#829cb9'}},
        {selector:'.selected-path',style:{'border-color':'#193f2c','border-width':4}},
        {selector:'edge.selected-path',style:{'width':3,'opacity':1}},
        {selector:':selected',style:{'overlay-color':'#236347','overlay-opacity':.12}},
        {selector:'.filtered',style:{'display':'none'}}
      ]});
    cy.on('tap','node, edge',event => showDetails(event.target));
    cy.on('tap',event => { if (event.target === cy) cy.elements().removeClass('selected-path'); });
  }

  function shown() { return cy.elements().filter(element=>!element.hasClass('filtered')); }

  function arrange() {
    if (!cy || !payload) return;
    const nodes=shown().nodes();
    if (!nodes.length) return;
    const positions={}, mode=el('graph-focus').value;
    const put=(collection,x,y,columns=1,dx=180,dy=110)=>collection.forEach((n,i)=>{
      positions[n.id()]={x:x+(i%columns)*dx,y:y+Math.floor(i/columns)*dy};
    });
    if (mode === 'revisions') {
      const memories=nodes.filter(n=>n.data('type')==='Memory').sort((a,b)=>
        (props(a).valid_from||0)-(props(b).valid_from||0) || a.id().localeCompare(b.id()));
      put(memories,130,300,memories.length,300);
      const used=new Set();
      memories.forEach(memory=>{
        const sources=memory.incomers('edge[type="SUPPORTS"]').sources().filter(n=>!n.hasClass('filtered'));
        sources.forEach((source,i)=>{
          if (!used.has(source.id())) positions[source.id()]={x:positions[memory.id()].x,y:70-i*100};
          used.add(source.id());
        });
      });
    } else if (mode === 'handoff') {
      put(nodes.filter(n=>n.data('type')==='Agent'),100,70,2,500);
      put(nodes.filter(n=>n.data('type')==='Task'),350,180);
      put(nodes.filter(n=>n.data('type')==='TaskResult'),600,270);
      const memories=nodes.filter(n=>n.data('type')==='Memory');
      put(memories,130,310,2,230);
      put(nodes.filter(n=>n.data('type')==='Message'),130,460,2,230);
    } else {
      put(nodes.filter(n=>n.data('type')==='Message'),80,80,2,200,110);
      put(nodes.filter(n=>n.data('type')==='Memory'),500,80,2,210,115);
      put(nodes.filter(n=>n.data('type')==='Agent'),980,80);
      put(nodes.filter(n=>n.data('type')==='Task'),980,420);
      put(nodes.filter(n=>n.data('type')==='TaskResult'),1190,420);
      put(nodes.filter(n=>structural.has(n.data('type'))),1420,80,2,160,100);
    }
    nodes.forEach((node,i)=>{if (!positions[node.id()]) positions[node.id()]={x:i*180,y:700};});
    // Bounded preset layout: no simulation, animation or database writes.
    nodes.layout({name:'preset',positions,fit:true,padding:48,animate:false}).run();
    cy.fit(shown(),48);
  }

  function revisionNote() {
    const revision = cy.edges('[type="SUPERSEDES"]').first();
    if (!revision.length) return 'No SUPERSEDES relationship in this graph.';
    const newer=props(revision.source()), older=props(revision.target());
    return `Timeline: ${older.object || short(older.content,25)} → ${newer.object || short(newer.content,25)}. Graph arrow: new SUPERSEDES previous.`;
  }

  function focus(mode='all') {
    if (!cy || !payload) return;
    el('graph-focus').value = mode;
    let visible;
    if (mode === 'revisions') {
      const revisions=cy.edges('[type="SUPERSEDES"]');
      if (!revisions.length) { focus('all'); el('graph-revision-note').textContent='No SUPERSEDES relationship to focus on.'; return; }
      const memories=revisions.sources().union(revisions.targets());
      const evidence=memories.incomers('edge[type="SUPPORTS"]');
      visible=memories.union(revisions).union(evidence).union(evidence.sources());
    } else if (mode === 'handoff') {
      let nodes=cy.nodes().filter(n => ['Agent','Task','TaskResult'].includes(n.data('type')));
      const used=nodes.outgoers('edge[type="USES_MEMORY"]');
      nodes=nodes.union(used.targets());
      const evidence=nodes.incomers('edge[type="SUPPORTS"]');
      nodes=nodes.union(evidence.sources());
      visible=nodes.union(nodes.edgesWith(nodes));
    } else {
      const nodes=el('graph-structure').checked ? cy.nodes() : cy.nodes().filter(n => !structural.has(n.data('type')));
      visible=nodes.union(nodes.edgesWith(nodes));
    }
    cy.batch(()=>{cy.elements().addClass('filtered').removeClass('selected-path');visible.removeClass('filtered');});
    cy.style().update();
    el('graph-count').textContent=`${visible.nodes().length}/${cy.nodes().length} nodes · ${visible.edges().length}/${cy.edges().length} edges`;
    el('graph-revision-note').textContent=revisionNote();
    arrange();
  }

  function showDetails(element) {
    cy.elements().removeClass('selected-path');
    element.closedNeighborhood().addClass('selected-path');
    const box=el('graph-details'), data=element.data(), p=data.properties;
    box.replaceChildren(make('h3',element.isNode() ? data.type+(data.kind?' · '+data.kind:'') : data.type));
    if (element.isEdge()) box.append(make('p',`${element.source().data('label')} → ${element.target().data('label')}`));
    if (p.content || p.prompt) box.append(make('p',p.content || p.prompt,'graph-content'));
    const fields=make('dl');
    for (const key of ['id','status','subject','predicate','object','task_type','instruction','created_at','updated_at','valid_from','valid_to','at','version','task_id']) {
      if (p[key] === undefined) continue;
      let value=p[key];
      if (['created_at','updated_at','valid_from','valid_to','at'].includes(key)) value=value ? new Date(value).toISOString() : 'Open / not recorded';
      fields.append(make('dt',key.replaceAll('_',' ')),make('dd',String(value)));
    }
    box.append(fields);
    if (element.isNode()) {
      let memories=element.data('type') === 'Memory' ? element : element.outgoers('edge[type="USES_MEMORY"]').targets();
      let sources=memories.incomers('edge[type="SUPPORTS"]').sources();
      sources=sources.union(element.incomers('edge[type="REQUESTED"]').sources().filter(n=>n.data('type')==='Message'));
      if (element.data('type') === 'Message') sources=sources.union(element);
      box.append(make('h4','Source messages in this bounded view'));
      if (!sources.length) box.append(make('p','No source Message loaded for this node.'));
      for (const source of sources) {
        const sp=props(source), card=make('div',undefined,'graph-source');
        card.append(make('code',sp.id || source.id()),make('p',sp.content || ''));
        box.append(card);
      }
    }
    const raw=make('details');raw.append(make('summary','Stored properties'),make('pre',JSON.stringify(p,null,2)));
    box.append(raw);
  }

  async function load(context=selected) {
    selected={...context};
    el('graph-context').value=selected.demoId ? `demo:${selected.user}` : `current:${selected.user}`;
    invalidate('Loading the selected graph…','loading');
    const request=serial, requested={...selected};
    el('graph-scope').textContent=`${requested.demoId?'DEMO':'CURRENT'} · ${requested.user.toUpperCase()}`;
    init();
    if (!cy) { overlay('Graph renderer unavailable. Check the local Cytoscape asset.','error'); return; }
    controller=new AbortController();
    const url=`/api/${requested.user}/graph`+(requested.demoId?`?demo_id=${encodeURIComponent(requested.demoId)}`:'');
    try {
      const response=await fetch(url,{signal:controller.signal});
      const data=await response.json();
      if (request !== serial) return;
      if (!response.ok) {
        if (response.status === 503) onConnection(false);
        throw Error(typeof data.detail === 'string' ? data.detail : 'Graph query failed.');
      }
      payload=data;
      const nodes=data.nodes.map(node => {
        const d={...node.data,label:label(node.data)};
        return {data:d,classes:structural.has(d.type)?'structural':''};
      });
      cy.add([...nodes,...data.edges]);
      el('graph-read').textContent=`${data.graph_name} · Read ${new Date(data.read_at).toLocaleTimeString()}${data.truncated?' · PARTIAL VIEW (limit reached)':''}`;
      el('graph-details').replaceChildren(make('p','Click a node or edge to inspect the stored properties and source paths.'));
      overlay(nodes.length?'':'This user graph has no stored nodes.','ready');
      controls(nodes.length > 0);
      onConnection(true);
      focus('all');
    } catch (error) {
      if (error.name === 'AbortError' || request !== serial) return;
      if (error instanceof TypeError) onConnection(false);
      invalidate(`Graph unavailable — ${error.message} Previous graph cleared.`, 'stale');
    }
  }

  function registerDemo(prefix) {
    const match=prefix.match(/_demo_([0-9a-f]{10})$/);
    if (!match) throw Error('Unexpected demo graph identity');
    latestDemo=match[1];
    el('graph-context').querySelectorAll('[data-demo-option]').forEach(option=>option.remove());
    for (const user of ['alice','bob']) {
      const option=make('option',`${user === 'alice'?'Alice':'Bob'} · latest demo`);
      option.value=`demo:${user}`; option.dataset.demoOption='true';
      el('graph-context').append(option);
    }
    return load({user:'alice',demoId:latestDemo});
  }

  el('graph-context').onchange=()=>{
    const [scope,user]=el('graph-context').value.split(':');
    load({user,demoId:scope==='demo'?latestDemo:null});
  };
  el('graph-reload').onclick=()=>load();
  el('graph-fit').onclick=()=>cy && cy.fit(shown(),36);
  el('graph-arrange').onclick=arrange;
  el('graph-revisions').onclick=()=>focus('revisions');
  el('graph-handoff').onclick=()=>focus('handoff');
  el('graph-focus').onchange=()=>focus(el('graph-focus').value);
  el('graph-structure').onchange=()=>focus('all');
  el('graph-zoom-in').onclick=()=>cy && cy.zoom({level:Math.min(cy.zoom()*1.3,cy.maxZoom()),renderedPosition:{x:cy.width()/2,y:cy.height()/2}});
  el('graph-zoom-out').onclick=()=>cy && cy.zoom({level:Math.max(cy.zoom()/1.3,cy.minZoom()),renderedPosition:{x:cy.width()/2,y:cy.height()/2}});
  controls(false);
  window.MemoryGraph={loadCurrent:user=>load({user,demoId:null}),registerDemo,invalidate,
    setConnectionHandler:handler=>{onConnection=handler;},get cy(){return cy;},get context(){return {...selected};}};
})();
