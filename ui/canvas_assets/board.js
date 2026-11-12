// All external text is inserted with textContent, never interpreted as HTML or code.
export default function({data, parentElement, setStateValue, setTriggerValue}) {
  const root = parentElement.querySelector('.canvas-root');
  root.replaceChildren();
  const make = (tag, cls, text, parent) => {
    const el = document.createElement(tag); if(cls) el.className=cls;
    if(text !== undefined) el.textContent=text; if(parent) parent.append(el); return el;
  };
  let layout = structuredClone(data.layout || {});
  let view = layout.view || {x:0,y:0,scale:1};
  const toolbar=make('div','toolbar',undefined,root);
  const viewport=make('div','viewport',undefined,root);
  viewport.setAttribute('aria-label','Interactive canvas');
  const world=make('div','world',undefined,viewport);
  const persist=()=>{layout.view=view;setStateValue('layout',layout);};
  const transform=()=>{world.style.transform=`translate(${view.x}px,${view.y}px) scale(${view.scale})`;};
  const button=(label,action,parent=toolbar)=>{const b=make('button','',label,parent);b.type='button';b.onclick=action;return b;};
  const zoom=(factor)=>{view.scale=Math.max(.3,Math.min(2,view.scale*factor));transform();persist();};
  button('Zoom in',()=>zoom(1.2));button('Zoom out',()=>zoom(1/1.2));
  button('Reset view',()=>{view={x:0,y:0,scale:1};transform();persist();});
  button('Fit board',()=>{
    let maxX=360,maxY=560;
    for(const [id,pos] of Object.entries(layout)) if(id!=='view') {maxX=Math.max(maxX,pos.x+680);maxY=Math.max(maxY,pos.y+560);}
    view={x:10,y:10,scale:Math.max(.15,Math.min(1,(viewport.clientWidth-20)/maxX,640/maxY))};transform();persist();
  });
  make('span','',`${data.visuals.length} diagrams · layouts retained during this session`,toolbar);
  let drag=null;
  const startDrag=(event,id)=>{
    if(event.button!==0 || event.target.closest('button,textarea')) return;
    const pos=id ? layout[id] : view;
    drag={id,x:event.clientX,y:event.clientY,ox:pos.x,oy:pos.y};
    viewport.setPointerCapture(event.pointerId);event.preventDefault();
  };
  viewport.onpointerdown=e=>{if(e.target===viewport||e.target===world)startDrag(e,null);};
  viewport.onpointermove=e=>{
    if(!drag)return;
    const divisor=drag.id?view.scale:1;
    const pos={x:drag.ox+(e.clientX-drag.x)/divisor,y:drag.oy+(e.clientY-drag.y)/divisor};
    if(drag.id){layout[drag.id]=pos;place(cards.get(drag.id),pos);}else{view.x=pos.x;view.y=pos.y;transform();}
  };
  viewport.onpointerup=()=>{if(drag){drag=null;persist();}};
  viewport.onpointercancel=()=>{drag=null;};
  const cards=new Map();
  const place=(card,pos)=>{card.style.left=pos.x+'px';card.style.top=pos.y+'px';};
  const card=(id,title,x,y,chat=false)=>{
    layout[id] ||= {x,y};
    const el=make('section','card'+(chat?' chat':''),undefined,world);cards.set(id,el);place(el,layout[id]);
    const handle=make('div','handle',undefined,el);make('span','',title,handle);
    handle.tabIndex=0;handle.setAttribute('aria-label',title+'. Drag or use arrow keys to move.');
    handle.onpointerdown=e=>startDrag(e,id);
    handle.onkeydown=e=>{
      const moves={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};
      if(moves[e.key]){e.preventDefault();layout[id].x+=moves[e.key][0];layout[id].y+=moves[e.key][1];place(el,layout[id]);persist();}
    };
    if(!chat)button('Remove',()=>setTriggerValue('remove',id),handle);
    return el;
  };
  if(!data.diagram_only) {
  const chat=card('chat','AI chat',16,16,true);
  const messages=make('div','messages',undefined,chat);messages.setAttribute('aria-live','polite');
  if(!data.messages.length)make('p','','Ask “Show the workflow”, “Map the main concepts”, or a question that needs no diagram.',messages);
  for(const msg of data.messages){const row=make('div','message',undefined,messages);make('strong','',msg.role==='user'?'You':'AI',row);make('span','',msg.content,row);}
  messages.scrollTop=messages.scrollHeight;
  const status=make('div','status'+(data.error?' error':''),data.error||'',chat);status.setAttribute('role','status');
  const form=make('form','',undefined,chat);
  const input=make('textarea','',undefined,form);input.maxLength=data.input_max_length||6000;input.required=true;input.setAttribute('aria-label','Message to AI');input.placeholder='Ask about your workflow or explore an idea…';
  const send=make('button','','Send',form);send.type='submit';
  form.onsubmit=e=>{e.preventDefault();if(!input.value.trim())return;send.disabled=true;input.disabled=true;status.textContent='Thinking and preparing diagrams…';setTriggerValue('submit',{id:crypto.randomUUID(),message:input.value.trim()});};
  }
  const ns='http://www.w3.org/2000/svg';
  const svgEl=(tag,attrs,parent,text)=>{const el=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(text!==undefined)el.textContent=text;parent.append(el);return el;};
  data.visuals.forEach((visual,index)=>{
    const el=card(visual.id,`${visual.kind==='mindmap'?'Mindmap':'Workflow'} · ${visual.title}`,data.diagram_only?10:380+(index%2)*700,16+Math.floor(index/2)*590,!!data.diagram_only);
    if(data.diagram_only) el.style.width=Math.max(620, viewport.clientWidth-30)+'px';
    make('div','note',visual.note,el);
    const container=make('div','diagram',undefined,el);
    const details=make('div','details','Select a node or transition to inspect its details.',el);
    const nodes=visual.nodes, positions=new Map();
    const names=new Map(nodes.map(n=>[n.id,n.label]));
    const showDetails=(item,isEdge)=>{
      details.replaceChildren();
      const d=item.details||{};
      const row=(label,value)=>{if(value!==null && value!==undefined && value!==''){const line=make('div','',undefined,details);make('strong','',label+': ',line);make('span','',String(value),line);}};
      row(isEdge?'Transition':'Step',isEdge?`${names.get(item.source)||item.source} → ${names.get(item.target)||item.target}`:item.label);
      row('Condition',d.condition|| (isEdge?item.label:null));row('Actor',d.actor||'Not stated');
      if(typeof d.inferred==='boolean')row('Inferred',d.inferred?'Yes':'No');row('Reason',d.inference_reason);
      if(d.source_passages?.length){make('strong','','Linked source passages',details);for(const passage of d.source_passages)make('p','',passage,details);}
      else if(d.evidence?.length) row('Source', 'Open Extraction Inspector to view linked passages.');
    };
    if(visual.kind==='mindmap'){
      const parent=new Map(visual.edges.map(e=>[e.target,e.source]));
      const rows=new Map();
      for(const node of nodes){let depth=0,current=node.id;const seen=new Set();while(parent.has(current)&&!seen.has(current)){seen.add(current);current=parent.get(current);depth++;}const row=rows.get(depth)||0;rows.set(depth,row+1);positions.set(node.id,{x:30+depth*230,y:40+row*100});}
    } else {
      // A grid guarantees bounded layout even for cyclic/disconnected workflows.
      nodes.forEach((n,i)=>positions.set(n.id,{x:40+(i%3)*240,y:50+Math.floor(i/3)*150}));
    }
    const width=Math.max(620,...[...positions.values()].map(p=>p.x+220));
    const height=Math.max(320,...[...positions.values()].map(p=>p.y+100));
    const svg=svgEl('svg',{width,height,role:'img','aria-label':visual.title},container);
    const defs=svgEl('defs',{},svg), marker=svgEl('marker',{id:'arrow-'+visual.id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:6,markerHeight:6,orient:'auto-start-reverse'},defs);
    svgEl('path',{d:'M 0 0 L 10 5 L 0 10 z',style:'fill:#777'},marker);
    const parallel=new Map();
    for(const edge of visual.edges){
      const a=positions.get(edge.source),b=positions.get(edge.target);if(!a||!b)continue;
      const key=edge.source+'|'+edge.target, lane=parallel.get(key)||0;parallel.set(key,lane+1);
      const sx=a.x+180,sy=a.y+24,tx=b.x,ty=b.y+24,bend=35+lane*30;
      const d=edge.source===edge.target?`M ${sx} ${sy} C ${sx+70+bend} ${sy-90} ${a.x-40} ${sy-90} ${a.x} ${ty}`:`M ${sx} ${sy} C ${sx+bend} ${sy-bend} ${tx-bend} ${ty-bend} ${tx} ${ty}`;
      const path=svgEl('path',{d,'marker-end':visual.kind==='workflow'?`url(#arrow-${visual.id})`:'',tabindex:0,'aria-label':edge.label||'Topic relationship'},svg);
      const inspect=()=>showDetails(edge,true);path.onclick=inspect;path.onkeydown=e=>{if(e.key==='Enter')inspect();};
      svgEl('title',{},path,edge.label||'Transition');
      svgEl('text',{x:(sx+tx)/2,y:(sy+ty)/2-bend/2},svg,edge.label.length>28?edge.label.slice(0,28)+'…':edge.label);
    }
    for(const node of nodes){const p=positions.get(node.id);const group=svgEl('g',{tabindex:0,role:'button','aria-label':node.label},svg);svgEl('rect',{x:p.x,y:p.y,width:180,height:48,rx:8},group);const words=node.label.split(/\s+/);const lines=[''];for(const word of words){let i=lines.length-1;if((lines[i]+' '+word).trim().length>23 && lines[i])lines.push(word);else lines[i]=(lines[i]+' '+word).trim();}const visible=lines.slice(0,2);if(lines.length>2)visible[1]+='…';visible.forEach((line,i)=>svgEl('text',{x:p.x+8,y:p.y+(visible.length===1?28:19+i*16)},group,line.length>25?line.slice(0,24)+'…':line));svgEl('title',{},group,node.label);const inspect=()=>showDetails(node,false);group.onclick=inspect;group.onkeydown=e=>{if(e.key==='Enter')inspect();};}
  });
  transform();
  return ()=>{viewport.onpointermove=null;viewport.onpointerup=null;};
}
