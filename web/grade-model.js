/* Forecasts and encrypted-vault scenario composition. No network or persistence side effects. */
(function(root){
  const Rules=typeof module!=='undefined'&&module.exports?require('./study-rules.js'):root.MasterPlanRules;
  const numeric=v=>typeof v==='number'&&Number.isFinite(v);
  const mark=v=>numeric(v)&&v>=1&&v<=6;
  const clamp=v=>Math.min(6,Math.max(1,v));
  function forecast(entry,target=4){
    const parts=entry?.parts||[],bonus=entry?.bonus??0;
    if(!Array.isArray(parts)||!parts.length||!numeric(bonus)||Math.abs(bonus)>6||parts.some(p=>!numeric(p.weight)||p.weight<=0||p.value!=null&&!mark(p.value)||p.estimate!=null&&!mark(p.estimate)))return {valid:false,complete:false};
    const weight=parts.reduce((s,p)=>s+p.weight,0),known=parts.filter(p=>p.value!=null),missing=parts.filter(p=>p.value==null),knownWeight=known.reduce((s,p)=>s+p.weight,0),missingWeight=weight-knownWeight;
    if(!numeric(weight)||!numeric(knownWeight))return {valid:false,complete:false};
    const knownSum=known.reduce((s,p)=>s+p.value*p.weight,0),projected=parts.every(p=>p.value!=null||p.estimate!=null)?clamp(parts.reduce((s,p)=>s+(p.value??p.estimate)*p.weight,0)/weight+bonus):null;
    const required=missingWeight>0&&mark(target)?((target-bonus)*weight-knownSum)/missingWeight:null;
    return {valid:true,complete:missing.length===0,weight,knownWeight,missingWeight,knownAverage:knownWeight?knownSum/knownWeight:null,
      value:missing.length===0?clamp(knownSum/weight+bonus):null,projected,min:clamp((knownSum+missingWeight)/weight+bonus),max:clamp((knownSum+missingWeight*6)/weight+bonus),
      required,reachable:required==null?null:required<=6,alreadySecured:required!=null&&required<=1};
  }
  const key=c=>c.number?`number:${String(c.number).replace(/\s+/g,'').toUpperCase()}${c.role==='case'||c.category==='case'?'@'+c.semester:''}`:`id:${c.id}`;
  function findActual(course,entries){
    const exact=entries.filter(e=>e.courseId===course.id||course.number&&e.number&&key(e)===key(course));
    if(exact.length===1)return exact[0];if(exact.length>1)return null;
    const name=String(course.title||'').trim().replace(/\s+/g,' ').toLowerCase();
    const names=entries.filter(e=>!e.number&&!e.courseId&&String(e.name||'').trim().replace(/\s+/g,' ').toLowerCase()===name);
    return names.length===1?names[0]:null;
  }
  function baseEntry(c){return {courseId:c.id,number:c.number||'',name:c.title,semester:c.semester,category:c.role,subtype:Rules.specialisationSubtype(c),
    countsForFinal:Rules.credited(c)&&['core','elective','specialisation','thesis'].includes(c.role)&&!(c.role==='specialisation'&&Rules.specialisationSubtype(c)==='seminar'),bonus:0,parts:[{id:'exam',name:'Exam',weight:100,value:null,estimate:null}]};}
  function simulationEntry(c,stored,realEntries,useActual){
    const base=baseEntry(c),draft=stored?structuredClone(stored):base,real=useActual?findActual(c,realEntries):null;
    const result={...draft,...base,bonus:draft.bonus??0,parts:structuredClone(draft.parts||base.parts),actualMatched:!!real};
    if(real){
      // Actual assessment structure/known results are authoritative. Assumptions only fill gaps.
      result.parts=(real.parts||[]).map((p,index)=>{const simulation=(draft.parts||[]).find(x=>p.id&&x.id===p.id)||draft.parts?.find(x=>x.name===p.name)||draft.parts?.[index];return {...p,id:p.id||`part-${index}`,value:p.value??null,estimate:p.value!=null?null:simulation?.estimate??null,actualLocked:p.value!=null,structureLocked:true};});
      const knownBonus=real.bonusKnown??(real.bonus!=null);result.bonus=knownBonus?(real.bonus??0):(draft.bonus??0);result.bonusLocked=knownBonus;
    }
    return result;
  }
  function projectedEntries(entries){return entries.map(e=>({...e,parts:e.parts.map(p=>({...p,value:p.value??p.estimate??null}))}));}
  function scenarioCourses(plan,history){const found=new Map();for(const c of Rules.allCourses(plan,history||[]))if(!found.has(key(c)))found.set(key(c),c);return [...found.values()];}
  function validateVault(value){
    if(!value||!Array.isArray(value.entries)||!value.entries.every(e=>e&&typeof e.name==='string'&&Array.isArray(e.parts)&&e.parts.every(p=>p&&typeof p.name==='string'&&numeric(p.weight)&&p.weight>0&&(p.value==null||mark(p.value))&&(p.estimate==null||mark(p.estimate)))))throw Error('Invalid grade vault');
    if(value.simulations!=null&&(!Array.isArray(value.simulations)||!value.simulations.every(s=>s&&typeof s.id==='string'&&typeof s.name==='string'&&typeof s.planId==='string'&&s.entries&&typeof s.entries==='object'&&!Array.isArray(s.entries))))throw Error('Invalid simulation data');
    return {...value,entries:value.entries,simulations:value.simulations||[]};
  }
  const api={forecast,key,findActual,baseEntry,simulationEntry,projectedEntries,scenarioCourses,validateVault};root.MasterPlanGrades=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
