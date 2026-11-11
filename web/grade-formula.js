/* Small arithmetic language. No JavaScript evaluation, property access or external functions. */
(function(root){
  const finite=n=>typeof n==='number'&&Number.isFinite(n);
  function parse(source){
    if(typeof source!=='string'||!source.trim()||source.length>500)throw Error('Formel fehlt/zu lang · Missing/oversized formula');
    const tokens=[];let pos=0;
    while(pos<source.length){const m=/^\s*(?:(\d+(?:\.\d*)?|\.\d+)|([A-Za-z][A-Za-z0-9_]*)|([+\-*/(),]))/.exec(source.slice(pos));if(!m){if(!source.slice(pos).trim())break;throw Error('Ungültiges Formelzeichen · Invalid formula character');}tokens.push(m[1]!=null?{number:Number(m[1])}:m[2]||m[3]);pos+=m[0].length;}
    let index=0,nodes=0;const variables=new Set();
    const make=node=>{if(++nodes>200)throw Error('Formel zu komplex · Formula too complex');return node;};
    function atom(){const t=tokens[index++];if(t&&typeof t==='object')return make({op:'number',value:t.number});
      if(t==='+'||t==='-')return make({op:t==='+'?'positive':'negative',args:[atom()]});
      if(t==='('){const a=expr();if(tokens[index++]!==')')throw Error('Klammer fehlt · Missing parenthesis');return a;}
      if(typeof t==='string'&&/^[A-Za-z][A-Za-z0-9_]*$/.test(t)){
        if(tokens[index]==='('){if(!['min','max'].includes(t))throw Error('Nur min/max erlaubt · Only min/max allowed');index++;const args=[expr()];while(tokens[index]===','){index++;args.push(expr());if(args.length>32)throw Error('Zu viele Argumente · Too many arguments');}if(tokens[index++]!==')'||args.length<2)throw Error('min/max benötigt mindestens zwei Werte · min/max needs at least two values');return make({op:t,args});}
        variables.add(t);return make({op:'variable',name:t});}
      throw Error('Formel unvollständig · Incomplete formula');}
    function product(){let a=atom();while(['*','/'].includes(tokens[index])){const op=tokens[index++];a=make({op,args:[a,atom()]});}return a;}
    function expr(){let a=product();while(['+','-'].includes(tokens[index])){const op=tokens[index++];a=make({op,args:[a,product()]});}return a;}
    const tree=expr();if(index!==tokens.length)throw Error('Unerwarteter Formeltext · Unexpected formula text');return {tree,variables:[...variables]};
  }
  function range(node,env){
    if(node.op==='number')return [node.value,node.value];if(node.op==='variable'){if(!Object.hasOwn(env,node.name))throw Error('Unbekannte Variable · Unknown variable: '+node.name);return env[node.name];}
    const a=node.args.map(n=>range(n,env)),[x,y]=a;
    switch(node.op){case 'positive':return x;case 'negative':return [-x[1],-x[0]];case '+':return [x[0]+y[0],x[1]+y[1]];case '-':return [x[0]-y[1],x[1]-y[0]];
      case '*':{const v=[x[0]*y[0],x[0]*y[1],x[1]*y[0],x[1]*y[1]];return [Math.min(...v),Math.max(...v)];}
      case '/':if(y[0]<=0&&y[1]>=0)throw Error('Division durch null möglich · Division by zero possible');return range({op:'*',args:[{op:'variable',name:'X'},{op:'variable',name:'Y'}]},{X:x,Y:[1/y[1],1/y[0]]});
      case 'min':return [Math.min(...a.map(v=>v[0])),Math.min(...a.map(v=>v[1]))];case 'max':return [Math.max(...a.map(v=>v[0])),Math.max(...a.map(v=>v[1]))];default:throw Error('Invalid operation');}
  }
  function variable(part,index){return part.variable||`P${index+1}`;}
  function analyze(entry,target=4){
    try{
      const parsed=parse(entry.formula),parts=entry.parts||[],bonus=entry.bonus??0,ceiling=entry.gradeCeiling??6;
      if(!parts.length||parts.length>100||!finite(bonus)||Math.abs(bonus)>6||!finite(ceiling)||ceiling<1||ceiling>6)throw Error('Ungültiger Bonus/Notenbereich · Invalid bonus/grade ceiling');
      const env={},estimates={},missing=[];const names=new Set();
      parts.forEach((p,i)=>{const name=variable(p,i);if(!/^[A-Za-z][A-Za-z0-9_]*$/.test(name)||['min','max','B'].includes(name)||names.has(name))throw Error('Ungültige/doppelte Variable · Invalid/duplicate variable: '+name);names.add(name);
        for(const v of [p.value,p.estimate])if(v!=null&&(!finite(v)||v<1||v>6))throw Error('Note außerhalb 1–6 · Grade outside 1–6');
        env[name]=p.value==null?[1,6]:[p.value,p.value];const e=p.value??p.estimate;estimates[name]=e==null?[1,6]:[e,e];if(p.value==null&&parsed.variables.includes(name))missing.push(name);});
      const inside=entry.bonusPlacement==='formula';if(inside){env.B=[bonus,bonus];estimates.B=[bonus,bonus];}else if(parsed.variables.includes('B'))throw Error('Für B Bonusplatzierung „in Formel“ wählen · Select in-formula bonus placement for B');
      const finish=v=>Math.min(ceiling,Math.max(1,v+(inside?0:bonus)));
      const bounds=range(parsed.tree,env),projected=range(parsed.tree,estimates);
      if([...bounds,...projected].some(v=>!finite(v)))throw Error('Nicht endliches Formelergebnis · Non-finite formula result');
      const complete=missing.length===0||Math.abs(finish(bounds[1])-finish(bounds[0]))<1e-10;
      const known=parts.filter(p=>p.value!=null),weight=parts.reduce((s,p)=>s+(p.weight||0),0),knownWeight=known.reduce((s,p)=>s+(p.weight||0),0);
      let required=null,reachable=null,alreadySecured=false;
      if(missing.length&&finite(target)&&target>=1&&target<=6){
        // Numerical search on a common grade for pending components. Not a symbolic guarantee.
        const at=v=>{const filled={...env};missing.forEach(name=>filled[name]=[v,v]);return finish(range(parsed.tree,filled)[0]);};
        if(at(1)>=target){required=1;reachable=true;alreadySecured=true;}else{let previous=1;for(let i=1;i<=2000;i++){const v=1+5*i/2000;if(at(v)>=target){let lo=previous,hi=v;for(let j=0;j<30;j++){const mid=(lo+hi)/2;if(at(mid)>=target)hi=mid;else lo=mid;}required=hi;reachable=true;break;}previous=v;}if(required==null)reachable=false;}
      }
      return {valid:true,formula:true,complete,weight,knownWeight,missingWeight:weight-knownWeight,knownAverage:known.length?known.reduce((s,p)=>s+p.value,0)/known.length:null,
        value:complete?finish(bounds[0]):null,projected:Math.abs(projected[1]-projected[0])<1e-9?finish(projected[0]):null,min:finish(bounds[0]),max:finish(bounds[1]),required,reachable,alreadySecured};
    }catch(e){return {valid:false,complete:false,error:e.message};}
  }
  const api={parse,analyze,variable};root.MasterPlanFormula=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
