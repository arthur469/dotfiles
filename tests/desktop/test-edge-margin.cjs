// Production placement -> reservation -> native projection; no live input.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path'),os=require('os'),sp=require('child_process');
const q=process.env.PR43_TEST_QML||path.join(__dirname,'../../.config/quickshell');
const source=fs.readFileSync(path.join(q,'Bar.qml'),'utf8'),layout=fs.readFileSync(path.join(q,'scripts/bar-layout.js'),'utf8').replace(/^\.pragma.*\n/,'');
function body(name){const start=source.indexOf('    function '+name+'(');assert(start>=0,name);const brace=source.indexOf('{',start);let depth=1,i=brace+1;while(depth){if(source[i]==='{')depth++;if(source[i]==='}')depth--;i++;}return source.slice(start,i);}
function fixture(position,margin,interior=false,scale=1,free=true,rotated=false){
 const width=900,height=600,vertical=['left','right'].includes(position),frame={x:0,y:0,width,height};
 const r=(vertical!==rotated)?{width:31.104,height:215.001}:{width:215.001,height:31.104};
 const x=interior?300:position==='right'?width-r.width-2:position==='top'||position==='bottom'?1.9:2;
 const y=interior?200:position==='bottom'?height-r.height-2:vertical?1.9:2;
 const window={screen:{width,height},layoutFrame:frame},panel={groupId:'free-resources',visible:true,width:r.width,height:r.height,hostWindow:window,model:['ws','cpu','ram','gpu','disk:fixture']};
 const c={Math,JSON,Object,BarLayout:{},cfg:{freeLayout:free,position},effEdge:margin*scale,vertical,layoutGroups:[{id:panel.groupId,x:x/(width-r.width),y:y/(height-r.height),position:.25}],bubblePanels:[panel],dragItem:null,dragGroupId:'',dragMoved:false,mergePanel:null,dragWindow:null,layoutAxis:vertical?'y':'x',layoutPriority:'',panelThick:28,bubblePadding:3};c.root=c;vm.createContext(c);vm.runInContext(layout,c.BarLayout=vm.createContext({}));
 vm.runInContext(['layoutSolution','groupPositions','reservationRect'].map(body).join('\n'),c);
 c.taskRect=()=>{const p=c.groupPositions(window,frame)[panel.groupId];return {x:p.x,y:p.y,width:r.width,height:r.height,output:'TEST'};};
 return {c,panel,window,frame};
}
let checked=0;const projections=[];
for(const position of ['left','right','top','bottom'])for(const margin of [4,12,24])for(const scale of [1,1.5])for(const free of [true,false])for(const rotated of [false,true]){
 const {c,panel}=fixture(position,margin,false,scale,free,rotated);const r=c.reservationRect(panel),vertical=['left','right'].includes(position),m=margin*scale;
 assert.equal(r.gapX,vertical?m:0,position+' corner: horizontal reservation changed after placement');
 assert.equal(r.gapY,vertical?0:m,position+' corner: vertical reservation changed after placement');
 if(free){if(position==='left')assert.equal(r.x,m);if(position==='right')assert(Math.abs(900-r.x-r.width-m)<.01);if(position==='top')assert.equal(r.y,m);if(position==='bottom')assert(Math.abs(600-r.y-r.height-m)<.01);}
 // A nearby native tiled window must leave the requested normal-axis margin.
 const box=position==='left'?{x:r.x+r.width-2,y:r.y+3,w:400,h:Math.max(24,Math.min(100,r.height-6))}:position==='right'?{x:r.x-400+2,y:r.y+3,w:400,h:Math.max(24,Math.min(100,r.height-6))}:position==='top'?{x:r.x+3,y:r.y+r.height-2,w:Math.max(32,Math.min(100,r.width-6)),h:400}:{x:r.x+3,y:r.y-400+2,w:Math.max(32,Math.min(100,r.width-6)),h:400};
 projections.push({r,box,side:position,margin:m});checked++;
}
for(const position of ['left','right','top','bottom']){
 const {c,panel}=fixture(position,12,true);let r=c.reservationRect(panel);assert.equal(r.gapX,12);assert.equal(r.gapY,12);checked++;
 for(const side of ['left','right','top','bottom']){
  const box=side==='left'?{x:r.x+r.width-2,y:r.y+5,w:400,h:20}:side==='right'?{x:r.x-400+2,y:r.y+5,w:400,h:20}:side==='top'?{x:r.x+5,y:r.y+r.height-2,w:20,h:400}:{x:r.x+5,y:r.y-400+2,w:20,h:400};
  // Native minimum target height is 24 px.
  if(box.h===20)box.h=24;if(box.w===20)box.w=32;
  projections.push({r,box,side,margin:12});
 }
 // Recompute after moving the same bubble to the edge, then back inside.
 c.layoutGroups[0].x=0;c.layoutGroups[0].y=.4;r=c.reservationRect(panel);assert.equal(r.gapX,12);assert.equal(r.gapY,0);
 c.layoutGroups[0].x=.4;c.layoutGroups[0].y=.4;r=c.reservationRect(panel);assert.equal(r.gapX,12);assert.equal(r.gapY,12);checked++;
}
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'43pr-edge-'));
try{
 const binary=path.join(folder,'project');sp.execFileSync(process.argv[2]||'c++',['-std=c++20',path.join(__dirname,'test-edge-margin.cpp'),'-o',binary],{stdio:'pipe'});
 const input=projections.map(({r,box})=>[box.x,box.y,box.w,box.h,r.x,r.y,r.width,r.height,r.gapX,r.gapY].join(' ')).join('\n')+'\n';
 const lines=sp.execFileSync(binary,{input,encoding:'utf8'}).trim().split('\n');assert.equal(lines.length,projections.length);
 lines.forEach((line,i)=>{const [x,y,w,h]=line.split(' ').map(Number),p=projections[i],r=p.r,m=p.margin;
  if(p.side==='left')assert(x>=r.x+r.width+m-.01);
  if(p.side==='right')assert(x+w<=r.x-m+.01);
  if(p.side==='top')assert(y>=r.y+r.height+m-.01);
  if(p.side==='bottom')assert(y+h<=r.y-m+.01);
 });
}finally{fs.rmSync(folder,{recursive:true,force:true});}
console.log(`PASS edge margin: ${checked} production placement/reservation cases and ${projections.length} native window projections; all edges, corners, local rotation, 1–1.5 scales, interior and attachment transitions`);
