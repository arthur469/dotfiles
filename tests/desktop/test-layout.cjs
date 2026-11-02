const fs=require('fs'),vm=require('vm'),assert=require('assert');const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../../.config/quickshell/scripts/bar-layout.js'),'utf8').replace(/^\.pragma.*\n/,''),c);
for(const [w,h] of [[1280,720],[3440,1440],[1920,1080],[1536,864]])for(const margin of [4,12,18]){
 for(const [edge,r] of [['left',{x:margin,y:h/3,width:40,height:150}],['right',{x:w-40-margin,y:h/3,width:40,height:150}],['top',{x:w/3,y:margin,width:150,height:40}],['bottom',{x:w/3,y:h-40-margin,width:150,height:40}]]){const p=c.edgePadding(r,w,h,margin,edge);assert.equal(p.edge,edge);assert.equal(p.gapX,['left','right'].includes(edge)?margin:0);assert.equal(p.gapY,['top','bottom'].includes(edge)?margin:0);}
 const p=c.edgePadding({x:w/3,y:h/3,width:40,height:60},w,h,margin,'left');assert.equal(p.edge,'');assert.equal(p.gapX,margin);assert.equal(p.gapY,margin);
 assert.equal(c.edgePadding({x:0,y:0,width:40,height:60},w,h,margin,'top').edge,'top');
}
const target={id:'a',x:150,y:150,width:100,height:100};assert.equal(c.placementTarget({x:75,y:175,width:100,height:30},[target],'').id,'a');assert.equal(c.placementTarget({x:1,y:1,width:10,height:10},[target],''),null);assert.equal(c.insertionSide({x:75,y:175,width:100,height:30},target),'left');
console.log('72 cas d’ancrage/résolution/marge, choix par rectangle et direction : PASS');
