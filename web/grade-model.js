/* Forecasts and encrypted-vault scenario composition. No network or persistence side effects. */
(function(root){
  const Rules=typeof module!=='undefined'&&module.exports?require('./study-rules.js'):root.MasterPlanRules;
  const numeric=v=>typeof v==='number'&&Number.isFinite(v);
  const mark=v=>numeric(v)&&v>=1&&v<=6;
  function forecast(entry,target=4){
    if(Rules.gradingMode(entry)==='pass-fail'){const outcome=entry.outcome||'pending',projectedOutcome=outcome==='pending'?(entry.assumedOutcome||'pending'):outcome;return {valid:['pass','fail','pending'].includes(outcome)&&['pass','fail','pending'].includes(projectedOutcome),passFail:true,complete:outcome!=='pending',outcome,projectedOutcome,value:null,projected:null};}
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
  function baseEntry(c){return {unitId:c.unitId||null,sourceSemester:c.sourceSemester||null,gradingMode:Rules.gradingMode(c),courseId:c.id,number:c.number||'',name:c.title,semester:c.semester,category:c.role,subtype:Rules.specialisationSubtype(c),
    countsForFinal:Rules.credited(c)&&['core','elective','specialisation','thesis'].includes(c.role)&&!(c.role==='specialisation'&&Rules.specialisationSubtype(c)==='seminar'),bonus:0,parts:[{id:'exam',name:'Exam',weight:100,value:null,estimate:null}]};}
  function simulationEntry(c,stored,realEntries,useActual){
    const base=baseEntry(c),draft=stored?structuredClone(stored):base,real=useActual?findActual(c,realEntries):null;
    const result={...draft,...base,bonus:draft.bonus??0,parts:structuredClone(draft.parts||base.parts),actualMatched:!!real,formulaLocked:false,statisticUnreachable:false};
    if(real)result.gradingMode=Rules.gradingMode(real);
    if(result.gradingMode==='pass-fail'){result.gradingMode='pass-fail';result.outcome=real?.outcome||'pending';result.assumedOutcome=draft.assumedOutcome||'pending';result.assumptionSource='pass-fail';result.outcomeLocked=!!real&&['pass','fail'].includes(real.outcome);return result;}
    if(real){
      result.formula=real.formula||'';result.formulaLocked=true;result.bonusPlacement=real.bonusPlacement||'after';result.gradeCeiling=real.gradeCeiling??6;
      // Actual assessment structure/known results are authoritative. Assumptions only fill gaps.
      result.parts=(real.parts||[]).map((p,index)=>{const simulation=(draft.parts||[]).find(x=>p.id&&x.id===p.id)||draft.parts?.find(x=>x.name===p.name)||draft.parts?.[index];return {...p,id:p.id||`part-${index}`,value:p.value??null,estimate:p.value!=null?null:simulation?.estimate??null,actualLocked:p.value!=null,structureLocked:true};});
      const knownBonus=real.bonusKnown??(real.bonus!=null);result.bonus=knownBonus?(real.bonus??0):(draft.bonus??0);result.bonusLocked=knownBonus;
      const target=draft.assumedModuleGrade??draft.statisticalGrade;
      if(target!=null&&result.parts.some(p=>p.value==null)){
        const estimate=forecast(result,target);
        result.statisticUnreachable=!estimate.valid||estimate.reachable===false||estimate.required==null||estimate.required>6;
        result.parts=result.parts.map(p=>p.value!=null?p:{...p,estimate:result.statisticUnreachable?null:Math.max(1,estimate.required)});
      }
    }
    return result;
  }
  function manualAssumption(entry){return !!entry&&(entry.assumptionMode==='manual'||mark(entry.overrideGrade)||!!entry.formula||!mark(entry.statisticalGrade)&&(entry.parts||[]).some(p=>mark(p.estimate)));}
  function assumptionDraft(c,stored,fallbackGrade){
    const draft=stored?structuredClone(stored):baseEntry(c);
    delete draft.assumedModuleGrade;
    if(Rules.gradingMode(c)==='pass-fail'){draft.gradingMode='pass-fail';draft.assumptionSource='pass-fail';return draft;}
    if(manualAssumption(draft)){
      draft.assumptionSource='manual';
      if(mark(draft.overrideGrade)){draft.assumedModuleGrade=draft.overrideGrade;draft.parts=baseEntry(c).parts;draft.parts[0].estimate=draft.overrideGrade;}
      return draft;
    }
    if(mark(draft.statisticalGrade)){draft.assumptionSource=draft.statistics?'statistics':'import';draft.assumedModuleGrade=draft.statisticalGrade;draft.parts=baseEntry(c).parts;draft.parts[0].estimate=draft.statisticalGrade;return draft;}
    if(mark(fallbackGrade)){draft.assumptionSource='fallback';draft.assumedModuleGrade=fallbackGrade;draft.parts=baseEntry(c).parts;draft.parts[0].estimate=fallbackGrade;return draft;}
    draft.assumptionSource='unknown';return draft;
  }
  function scenarioEntry(c,scenario,realEntries){
    const useActual=scenario.useActual??(scenario.planId==='actual'),real=useActual?findActual(c,realEntries):null,effective=real?{...c,gradingMode:Rules.gradingMode(real)}:c;
    const draft=assumptionDraft(effective,scenario.entries[key(c)],scenario.fallbackGrade),result=simulationEntry(effective,draft,realEntries,useActual);
    if(result.actualMatched&&(forecast(result,null).value!=null||result.outcomeLocked))result.assumptionSource='actual';
    return result;
  }
  function updateSigma(scenario,courses,factor,selectedKeys,{perCourse=false}={}){
    if(!numeric(factor)||Math.abs(factor)>10)throw Error('Ungültiger Faktor · Invalid factor');
    const X=typeof module!=='undefined'&&module.exports?require('./exchange.js'):root.MasterPlanExchange;
    const updates=[],selected=new Set(selectedKeys),summary={updated:0,preserved:0};
    for(const c of courses){const k=key(c),old=scenario.entries[k];if(!selected.has(k))continue;
      if(Rules.gradingMode(c)==='pass-fail'||!old?.statistics||manualAssumption(old)||old.sigmaPinned&&!perCourse){summary.preserved++;continue;}
      const grade=X.statisticalGrade(old.statistics,factor);
      if(grade==null){summary.preserved++;continue;}
      const next={...structuredClone(old),...baseEntry(c),statistics:structuredClone(old.statistics),assumptionMode:'statistics',statisticalGrade:grade,sigmaFactor:factor,sigmaPinned:perCourse};next.parts[0].estimate=grade;updates.push([k,next]);
    }
    for(const [k,next] of updates)scenario.entries[k]=next;if(!perCourse)scenario.sigmaFactor=factor;summary.updated=updates.length;return summary;
  }
  function setFallback(scenario,value){if(value!=null&&!mark(value))throw Error('Note muss zwischen 1 und 6 liegen · Grade must be between 1 and 6');scenario.fallbackGrade=value;}
  function setOverride(scenario,c,value){
    if(Rules.gradingMode(c)==='pass-fail')throw Error('Pass/Fail hat keine Zahlennote · Pass/fail has no numeric grade');
    if(!mark(value))throw Error('Note muss zwischen 1 und 6 liegen · Grade must be between 1 and 6');
    const old=scenario.entries[key(c)],next=baseEntry(c);if(old?.sigmaPinned){next.sigmaPinned=true;next.sigmaFactor=old.sigmaFactor;}if(old?.statistics)next.statistics=structuredClone(old.statistics);if(old?.importedScenario)next.importedScenario=structuredClone(old.importedScenario);
    next.assumptionMode='manual';next.overrideGrade=value;next.parts[0].estimate=value;scenario.entries[key(c)]=next;
  }
  function resetOverride(scenario,c){
    const old=scenario.entries[key(c)],next=baseEntry(c);const factor=old?.sigmaPinned?old.sigmaFactor:scenario.sigmaFactor??old?.sigmaFactor??0;if(old?.sigmaPinned)next.sigmaPinned=true;
    if(old?.statistics){const X=typeof module!=='undefined'&&module.exports?require('./exchange.js'):root.MasterPlanExchange;next.statistics=structuredClone(old.statistics);next.statisticalGrade=X.statisticalGrade(next.statistics,factor);next.sigmaFactor=factor;next.assumptionMode='statistics';next.parts[0].estimate=next.statisticalGrade;}
    else if(old?.importedScenario){next.importedScenario=structuredClone(old.importedScenario);next.statisticalGrade=next.importedScenario.grade??null;next.parts[0].estimate=next.statisticalGrade;}
    scenario.entries[key(c)]=next;
  }
  function projectedEntries(entries){return entries.map(e=>({...e,outcome:e.outcome==='pass'||e.outcome==='fail'?e.outcome:e.assumedOutcome||'pending',parts:e.parts.map(p=>({...p,value:p.value??p.estimate??null}))}));}
  function scenarioCourses(plan,history){const found=new Map();for(const c of Rules.allCourses(plan,history||[]))if(!found.has(key(c)))found.set(key(c),c);return [...found.values()];}
  function validateVault(value){
    if(!value||!Array.isArray(value.entries)||!value.entries.every(e=>e&&typeof e.name==='string'&&Array.isArray(e.parts)&&e.parts.every(p=>p&&typeof p.name==='string'&&numeric(p.weight)&&p.weight>0&&(p.value==null||mark(p.value))&&(p.estimate==null||mark(p.estimate)))))throw Error('Invalid grade vault');
    if(value.simulations!=null&&(!Array.isArray(value.simulations)||!value.simulations.every(s=>s&&typeof s.id==='string'&&typeof s.name==='string'&&typeof s.planId==='string'&&s.entries&&typeof s.entries==='object'&&!Array.isArray(s.entries))))throw Error('Invalid simulation data');
    for(const s of value.simulations||[]){if(s.fallbackGrade!=null&&!mark(s.fallbackGrade))throw Error('Invalid fallback grade');for(const e of Object.values(s.entries)){if(e?.overrideGrade!=null&&!mark(e.overrideGrade)||e?.assumptionMode!=null&&!['manual','statistics'].includes(e.assumptionMode))throw Error('Invalid grade assumption');}}
    for(const e of [...value.entries,...(value.simulations||[]).flatMap(s=>Object.values(s.entries))])if(e&&(e.gradingMode!=null&&!['numeric','pass-fail'].includes(e.gradingMode)||['outcome','assumedOutcome'].some(k=>e[k]!=null&&!['pending','pass','fail'].includes(e[k]))||e.sigmaPinned!=null&&typeof e.sigmaPinned!=='boolean'||e.sigmaFactor!=null&&(!numeric(e.sigmaFactor)||Math.abs(e.sigmaFactor)>10)))throw Error('Invalid assessment mode/outcome');
    if(value.activeSimulation!=null&&typeof value.activeSimulation!=='string')throw Error('Invalid selected scenario');
    if(value.statistics!=null){if(!Array.isArray(value.statistics)||value.statistics.length>100)throw Error('Invalid statistics library');const X=typeof module!=='undefined'&&module.exports?require('./exchange.js'):root.MasterPlanExchange;for(const d of value.statistics){if(d?.kind!=='masterplan-statistics')throw Error('Invalid statistics dataset');X.validate(d);}}
    return {...value,entries:value.entries,simulations:value.simulations||[],statistics:value.statistics||[]};
  }
  const api={forecast,key,findActual,baseEntry,simulationEntry,manualAssumption,assumptionDraft,scenarioEntry,updateSigma,setFallback,setOverride,resetOverride,projectedEntries,scenarioCourses,validateVault};root.MasterPlanGrades=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
