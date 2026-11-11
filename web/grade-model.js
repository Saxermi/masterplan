/* Forecasts and encrypted-vault scenario composition. No network or persistence side effects. */
(function(root){
  const Rules=typeof module!=='undefined'&&module.exports?require('./study-rules.js'):root.MasterPlanRules;
  const numeric=v=>typeof v==='number'&&Number.isFinite(v);
  const mark=v=>numeric(v)&&v>=1&&v<=6;
  function forecast(entry,target=4){
    if(entry?.formula){const F=typeof module!=='undefined'&&module.exports?require('./grade-formula.js'):root.MasterPlanFormula;return F.analyze(entry,target);}
    const parts=entry?.parts||[],bonus=entry?.bonus??0,ceiling=entry?.gradeCeiling??6;const bounded=v=>Math.min(ceiling,Math.max(1,v));
    if(!numeric(ceiling)||ceiling<1||ceiling>6||entry?.bonusPlacement==='formula')return {valid:false,complete:false,error:'Formel/Notengrenze prüfen · Check formula/grade ceiling'};
    if(!Array.isArray(parts)||!parts.length||!numeric(bonus)||Math.abs(bonus)>6||parts.some(p=>!numeric(p.weight)||p.weight<=0||p.value!=null&&!mark(p.value)||p.estimate!=null&&!mark(p.estimate)))return {valid:false,complete:false};
    const weight=parts.reduce((s,p)=>s+p.weight,0),known=parts.filter(p=>p.value!=null),missing=parts.filter(p=>p.value==null),knownWeight=known.reduce((s,p)=>s+p.weight,0),missingWeight=weight-knownWeight;
    if(!numeric(weight)||!numeric(knownWeight))return {valid:false,complete:false};
    const knownSum=known.reduce((s,p)=>s+p.value*p.weight,0),projected=parts.every(p=>p.value!=null||p.estimate!=null)?bounded(parts.reduce((s,p)=>s+(p.value??p.estimate)*p.weight,0)/weight+bonus):null;
    const required=missingWeight>0&&mark(target)?((target-bonus)*weight-knownSum)/missingWeight:null;
    return {valid:true,complete:missing.length===0,weight,knownWeight,missingWeight,knownAverage:knownWeight?knownSum/knownWeight:null,
      value:missing.length===0?bounded(knownSum/weight+bonus):null,projected,min:bounded((knownSum+missingWeight)/weight+bonus),max:bounded((knownSum+missingWeight*6)/weight+bonus),
      required,reachable:required==null?null:required<=6&&target<=ceiling,alreadySecured:required!=null&&required<=1};
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
    const result={...draft,...base,bonus:draft.bonus??0,parts:structuredClone(draft.parts||base.parts),actualMatched:!!real,formulaLocked:false,statisticUnreachable:false};
    if(real){
      result.formula=real.formula||'';result.formulaLocked=true;result.bonusPlacement=real.bonusPlacement||'after';result.gradeCeiling=real.gradeCeiling??6;
      // Actual assessment structure/known results are authoritative. Assumptions only fill gaps.
      result.parts=(real.parts||[]).map((p,index)=>{const simulation=(draft.parts||[]).find(x=>p.id&&x.id===p.id)||draft.parts?.find(x=>x.name===p.name)||draft.parts?.[index];return {...p,id:p.id||`part-${index}`,value:p.value??null,estimate:p.value!=null?null:simulation?.estimate??null,actualLocked:p.value!=null,structureLocked:true};});
      const knownBonus=real.bonusKnown??(real.bonus!=null);result.bonus=knownBonus?(real.bonus??0):(draft.bonus??0);result.bonusLocked=knownBonus;
      if(draft.statisticalGrade!=null&&result.parts.some(p=>p.value==null)){
        const estimate=forecast(result,draft.statisticalGrade);
        result.statisticUnreachable=!estimate.valid||estimate.reachable===false||estimate.required==null||estimate.required>6;
        result.parts=result.parts.map(p=>p.value!=null?p:{...p,estimate:result.statisticUnreachable?null:Math.max(1,estimate.required)});
      }
    }
    return result;
  }
  function projectedEntries(entries){return entries.map(e=>({...e,parts:e.parts.map(p=>({...p,value:p.value??p.estimate??null}))}));}
  function scenarioCourses(plan,history){const found=new Map();for(const c of Rules.allCourses(plan,history||[]))if(!found.has(key(c)))found.set(key(c),c);return [...found.values()];}
  function validateVault(value){
    if(!value||!Array.isArray(value.entries)||!value.entries.every(e=>e&&typeof e.name==='string'&&Array.isArray(e.parts)&&e.parts.every(p=>p&&typeof p.name==='string'&&numeric(p.weight)&&p.weight>0&&(p.value==null||mark(p.value))&&(p.estimate==null||mark(p.estimate)))))throw Error('Invalid grade vault');
    if(value.simulations!=null&&(!Array.isArray(value.simulations)||!value.simulations.every(s=>s&&typeof s.id==='string'&&typeof s.name==='string'&&typeof s.planId==='string'&&s.entries&&typeof s.entries==='object'&&!Array.isArray(s.entries))))throw Error('Invalid simulation data');
    if(value.statistics!=null){if(!Array.isArray(value.statistics)||value.statistics.length>100)throw Error('Invalid statistics library');const X=typeof module!=='undefined'&&module.exports?require('./exchange.js'):root.MasterPlanExchange;for(const d of value.statistics){if(d?.kind!=='masterplan-statistics')throw Error('Invalid statistics dataset');X.validate(d);}}
    return {...value,entries:value.entries,simulations:value.simulations||[],statistics:value.statistics||[]};
  }
  const api={forecast,key,findActual,baseEntry,simulationEntry,projectedEntries,scenarioCourses,validateVault};root.MasterPlanGrades=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
