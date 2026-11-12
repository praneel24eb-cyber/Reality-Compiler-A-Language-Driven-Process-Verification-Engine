// All model and user content is rendered as text, never executable markup.
export default function ({data, parentElement, setStateValue, setTriggerValue}) {
  const root = parentElement.querySelector('.canvas-root');
  root.replaceChildren();
  const make = (tag, cls, text, parent) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    if (parent) parent.append(el);
    return el;
  };
  let layout = structuredClone(data.layout || {});
  let view = layout.view || {x: 0, y: 0, scale: 1};
  const toolbar = make('div', 'toolbar', undefined, root);
  make('span', 'board-label', 'PROCESS CANVAS', toolbar);
  const tools = make('div', 'board-tools', undefined, toolbar);
  const viewport = make('div', 'viewport', undefined, root);
  viewport.setAttribute('aria-label', 'Interactive canvas');
  const world = make('div', 'world', undefined, viewport);
  const cards = new Map();
  let compact = false, drag = null;
  const persist = () => { layout.view = view; setStateValue('layout', layout); };
  const transform = () => { world.style.transform = compact ? '' : `translate(${view.x}px,${view.y}px) scale(${view.scale})`; };
  const button = (label, action, parent = tools) => {
    const b = make('button', '', label, parent); b.type = 'button'; b.onclick = action; return b;
  };
  const zoom = (factor) => {
    const next = Math.max(.2, Math.min(2, view.scale * factor));
    const cx = viewport.clientWidth / 2, cy = viewport.clientHeight / 2;
    view.x = cx - (cx - view.x) * next / view.scale;
    view.y = cy - (cy - view.y) * next / view.scale;
    view.scale = next; transform(); persist();
  };
  button('Zoom in', () => zoom(1.2)); button('Zoom out', () => zoom(1 / 1.2));
  button('Reset view', () => { view = {x:0,y:0,scale:1}; transform(); persist(); });
  button('Fit board', () => {
    if (!cards.size) return;
    const boxes = [...cards].map(([id, el]) => ({...layout[id], w:el.offsetWidth, h:el.offsetHeight}));
    const minX = Math.min(...boxes.map(b => b.x)), minY = Math.min(...boxes.map(b => b.y));
    const width = Math.max(...boxes.map(b => b.x+b.w))-minX;
    const height = Math.max(...boxes.map(b => b.y+b.h))-minY;
    const scale = Math.max(.15, Math.min(1, (viewport.clientWidth-40)/width, (viewport.clientHeight-40)/height));
    view = {x:20-minX*scale,y:20-minY*scale,scale}; transform(); persist();
  });
  make('span', 'visual-count', `${data.visuals.length} visual${data.visuals.length === 1 ? '' : 's'}`, toolbar);
  const place = (el, pos) => { el.style.left=pos.x+'px'; el.style.top=pos.y+'px'; };
  const startDrag = (event, id) => {
    if (compact || event.button !== 0 || event.target.closest('button,textarea')) return;
    const pos = id ? layout[id] : view;
    drag = {id,x:event.clientX,y:event.clientY,ox:pos.x,oy:pos.y};
    viewport.setPointerCapture(event.pointerId); event.preventDefault();
  };
  viewport.onpointerdown = e => { if (e.target===viewport || e.target===world) startDrag(e,null); };
  viewport.onpointermove = e => {
    if (!drag) return;
    const divisor = drag.id ? view.scale : 1;
    const pos = {x:drag.ox+(e.clientX-drag.x)/divisor,y:drag.oy+(e.clientY-drag.y)/divisor};
    if (drag.id) { layout[drag.id]=pos; place(cards.get(drag.id),pos); }
    else { view.x=pos.x;view.y=pos.y;transform(); }
  };
  viewport.onpointerup = () => { if(drag){drag=null;persist();} };
  viewport.onpointercancel = () => { drag=null; };
  const card = (id, title, kind, x, y, removable=true) => {
    layout[id] ||= {x,y};
    const el = make('section','card '+kind,undefined,world); cards.set(id,el); place(el,layout[id]);
    const handle = make('div','handle',undefined,el);
    make('span','card-symbol',kind==='chat'?'✦':kind==='mindmap'?'◎':'◇',handle);
    make('span','card-title',title,handle);
    handle.tabIndex=0; handle.setAttribute('aria-label',title+'. Drag or use arrow keys to move.');
    handle.onpointerdown=e=>startDrag(e,id);
    handle.onkeydown=e=>{
      const moves={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};
      if(moves[e.key]&&!compact){e.preventDefault();layout[id].x+=moves[e.key][0];layout[id].y+=moves[e.key][1];place(el,layout[id]);persist();}
    };
    if(removable) button('Remove',()=>setTriggerValue('remove',id),handle);
    return el;
  };
  let input;
  if (!data.diagram_only) {
    const chat=card('chat','Your process copilot','chat',20,20,false);
    make('div','chat-subtitle','Ask. Explore. Make the next step clear.',chat);
    const messages=make('div','messages',undefined,chat);messages.setAttribute('aria-live','polite');
    if(!data.messages.length){make('div','empty-chat-title','Start with a question.',messages);make('p','','I can explain your workflow, surface gaps, or map the ideas behind it.',messages);}
    for(const msg of data.messages){const row=make('div','message '+msg.role,undefined,messages);make('strong','',msg.role==='user'?'YOU':'COMPILER',row);make('div','message-text',msg.content,row);}
    messages.scrollTop=messages.scrollHeight;
    const status=make('div','status'+(data.error?' error':''),data.error||'',chat);status.setAttribute('role','status');
    const form=make('form','',undefined,chat);
    input=make('textarea','',undefined,form);input.maxLength=data.input_max_length||6000;input.required=true;
    input.setAttribute('aria-label','Message to AI');input.placeholder='Ask a question about your process…';
    const send=make('button','send','Send message ↗',form);send.type='submit';
    form.onsubmit=e=>{e.preventDefault();if(!input.value.trim())return;send.disabled=true;input.disabled=true;status.textContent='Preparing your response…';setTriggerValue('submit',{id:crypto.randomUUID(),message:input.value.trim()});};
  }
  if (!data.visuals.length && !data.diagram_only) {
    const empty=make('div','canvas-empty',undefined,world);
    make('div','empty-icon','◇',empty);make('h2','','Make your process visible.',empty);
    make('p','','Your workflow graphs and mindmaps appear here as you explore. Select a saved workflow above, or start from a goal in Workflow Builder.',empty);
    const prompts=make('div','prompt-chips',undefined,empty);
    for(const text of ['Show the workflow','Map the main concepts','Find missing paths'])button(text,()=>{input.value=text;input.focus();},prompts);
    make('small','','Drag to arrange · Pan to explore · Fit to see the whole board',empty);
  }
  const ns='http://www.w3.org/2000/svg';
  const svgEl=(tag,attrs,parent,text)=>{const el=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;parent.append(el);return el;};
  data.visuals.forEach((visual,index)=>{
    const el=card(visual.id,visual.title,visual.kind,data.diagram_only?20:390,20+index*680,!data.diagram_only);
    if(data.diagram_only)el.classList.add('wide');
    make('div','note',visual.note,el);
    const container=make('div','diagram',undefined,el);
    const details=make('div','details','Select a step or connection to see its source and responsibilities.',el);
    const nodes=visual.nodes, positions=new Map(), names=new Map(nodes.map(n=>[n.id,n.label]));
    const showDetails=(item,isEdge)=>{
      details.replaceChildren();
      const d=item.details||{};
      const row=(label,value)=>{if(value!==null&&value!==undefined&&value!==''){const line=make('div','detail-row',undefined,details);make('strong','',label,line);make('span','',String(value),line);}};
      row(isEdge?'Connection':'Step',isEdge?`${names.get(item.source)||item.source} → ${names.get(item.target)||item.target}`:item.label);
      row('Condition',d.condition||(isEdge?item.label:null));row('Responsible',d.actor||'Not stated');
      if(typeof d.inferred==='boolean')row('Inferred',d.inferred?'Yes — review required':'No');row('Reason',d.inference_reason);
      if(d.source_passages?.length){make('strong','source-heading','SOURCE EVIDENCE',details);for(const passage of d.source_passages)make('blockquote','',passage,details);}
    };
    const ranks=new Map(), outgoing=new Map(nodes.map(n=>[n.id,[]])), incoming=new Set(visual.edges.map(e=>e.target));
    for(const e of visual.edges)outgoing.get(e.source)?.push(e.target);
    let starts=nodes.filter(n=>n.details?.kind==='start'||!incoming.has(n.id));
    if(!starts.length&&nodes.length)starts=[nodes[0]];
    const queue=starts.map(n=>[n.id,0]);
    for(let i=0;i<queue.length;i++){const[id,rank]=queue[i];if(ranks.has(id))continue;ranks.set(id,rank);for(const next of outgoing.get(id)||[])if(!ranks.has(next))queue.push([next,rank+1]);}
    let disconnected=Math.max(0,...ranks.values())+1;
    for(const n of nodes)if(!ranks.has(n.id))ranks.set(n.id,disconnected++);
    const rows=new Map();
    for(const n of nodes){const rank=ranks.get(n.id),row=rows.get(rank)||0;rows.set(rank,row+1);positions.set(n.id,{x:38+rank*285,y:65+row*145});}
    const width=Math.max(550,...[...positions.values()].map(p=>p.x+260)),height=Math.max(330,...[...positions.values()].map(p=>p.y+135));
    const svg=svgEl('svg',{width,height,role:'img','aria-label':visual.title},container);
    const marker=svgEl('marker',{id:'arrow-'+visual.id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'},svgEl('defs',{},svg));
    svgEl('path',{d:'M 0 0 L 10 5 L 0 10 z',class:'arrow-head'},marker);
    const lanes=new Map();
    for(const edge of visual.edges){
      const a=positions.get(edge.source),b=positions.get(edge.target);if(!a||!b)continue;
      const pair=edge.source+'|'+edge.target,lane=lanes.get(pair)||0;lanes.set(pair,lane+1);
      const sx=a.x+210,sy=a.y+40,tx=b.x,ty=b.y+40,bend=30+lane*28;
      const d=edge.source===edge.target?`M ${sx} ${sy} C ${sx+65} ${sy-100-bend} ${a.x-45} ${sy-100-bend} ${a.x} ${ty}`:
        tx<=sx?`M ${sx} ${sy} C ${sx+75} ${sy+100+bend} ${tx-75} ${ty+100+bend} ${tx} ${ty}`:
        `M ${sx} ${sy} C ${sx+bend} ${sy-lane*24} ${tx-bend} ${ty-lane*24} ${tx} ${ty}`;
      const path=svgEl('path',{d,class:'connection','marker-end':`url(#arrow-${visual.id})`,tabindex:0,role:'button','aria-label':edge.label||'Topic relationship'},svg);
      path.onclick=()=>showDetails(edge,true);path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showDetails(edge,true);}};
      svgEl('title',{},path,edge.label||'Connection');
      if(edge.label)svgEl('text',{x:(sx+tx)/2,y:(sy+ty)/2-12-lane*25,class:'edge-label','text-anchor':'middle'},svg,edge.label.length>24?edge.label.slice(0,23)+'…':edge.label);
    }
    for(const node of nodes){
      const p=positions.get(node.id),kind=node.details?.kind||'topic';
      const group=svgEl('g',{tabindex:0,role:'button','aria-label':node.label,class:'node '+kind+(node.details?.inferred?' inferred':'')},svg);
      svgEl('rect',{x:p.x,y:p.y,width:210,height:82,rx:12},group);
      svgEl('text',{x:p.x+14,y:p.y+19,class:'node-kind'},group,kind==='normal'?'STEP':kind.toUpperCase());
      const words=node.label.split(/\s+/),lines=[''];
      for(const word of words){let i=lines.length-1;if((lines[i]+' '+word).trim().length>27&&lines[i])lines.push(word);else lines[i]=(lines[i]+' '+word).trim();}
      const visible=lines.slice(0,3);if(lines.length>3)visible[2]+='…';
      visible.forEach((line,i)=>svgEl('text',{x:p.x+14,y:p.y+38+i*16,class:'node-label'},group,line.length>29?line.slice(0,28)+'…':line));
      svgEl('title',{},group,node.label);
      const inspect=()=>{svg.querySelectorAll('.selected').forEach(n=>n.classList.remove('selected'));group.classList.add('selected');showDetails(node,false);};
      group.onclick=inspect;group.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect();}};
    }
    if(!nodes.length)make('p','empty-diagram','No process steps were extracted. Review the source pages before generating a workflow.',container);
  });
  const resize=()=>{compact=root.clientWidth<700;root.classList.toggle('compact',compact);transform();};
  const observer=new ResizeObserver(resize);observer.observe(root);resize();
  return()=>{observer.disconnect();viewport.onpointermove=null;viewport.onpointerup=null;};
}
