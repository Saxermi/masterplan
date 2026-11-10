/* Pure provisional degree checks, shared by the browser and dependency-free tests. */
(function(root) {
  'use strict';
  const roles=['core','specialisation','elective','case','project','sip','thesis','scientific','extra','requirement'];
  const statuses=['interested','planned','enrolled','completed'];
  const defaults=[
    {id:'total',minEcts:120,warningEcts:130}, {id:'main',minEcts:74},
    {id:'core',minEcts:12,minCourses:2,maxCourses:2},
    {id:'spec',minEcts:18,minLectures:4,maxLectures:4,minSeminars:1,maxSeminars:1},
    {id:'elective',minEcts:12,minCourses:2},
    {id:'case',minEcts:6,minCourses:2,courseEcts:3},
    {id:'project',minEcts:8,minCourses:1,maxCourses:1,courseEcts:8},
    {id:'sip',minEcts:2}, {id:'thesis',minEcts:30,minCourses:1,maxCourses:1,courseEcts:30},
    {id:'scientific',minEcts:0,minCourses:1}
  ];
  const number=c=>String(c.number||'').replace(/\s+/g,'').toUpperCase();
  const identity=c=>number(c)?`number:${number(c)}${c.role==='case'?'@'+c.semester:''}`:`id:${c.id}`;
  const validCredits=c=>typeof c.ects==='number'&&Number.isFinite(c.ects)&&c.ects>=0&&c.ects<=40;
  const credited=c=>roles.includes(c.role)&&!['extra','requirement','scientific'].includes(c.role)&&
    ['planned','enrolled','completed'].includes(c.status)&&c.creditApproved!==false&&c.usedForBSc!==true&&validCredits(c)&&c.ects>0;

  function allCourses(plan,history=[]) {
    // History records achievement; the plan controls its category and approval.
    const result=(plan.courses||[]).map(c=>({...c}));
    for(const record of history) {
      const matches=result.filter(c=>identity(c)===identity(record));
      if(matches.length)matches.forEach(c=>{c.status='completed';if(record.usedForBSc)c.usedForBSc=true;});
      else result.push({...record,status:'completed',locked:true});
    }
    return result;
  }

  function allocationKey(c,courses) {
    // Repeating Case Studies in different semesters is expressly required.
    // A different role on the same number cannot bypass module deduplication.
    if(c.role==='case'&&number(c)&&courses.some(x=>number(x)===number(c)&&x.role!=='case'&&credited(x)))
      return `number:${number(c)}`;
    return identity(c);
  }

  function uniqueCredits(courses) {
    const grouped=new Map();
    for(const c of courses.filter(c=>credited(c)&&!courses.some(other=>number(c)&&number(other)===number(c)&&(other.usedForBSc===true||other.role==='requirement'&&other.status!=='interested')))) {
      const key=allocationKey(c,courses), old=grouped.get(key);
      if(!old||c.status==='completed'&&old.status!=='completed')grouped.set(key,c);
    }
    return [...grouped.values()];
  }

  function audit(plan,history=[],rules={},scientificWorksBSc=false) {
    const courses=allCourses(plan,history), unique=uniqueCredits(courses);
    const issues=[];
    const issue=(code,key,message,severity='error',courseIds=[])=>issues.push({code,key,message,severity,courseIds});
    const limits=defaults.map(rule=>({...rule,...(rules.requirements||[]).find(r=>r.id===rule.id)}));
    for(const c of courses) {
      if(!roles.includes(c.role)||!statuses.includes(c.status)||!validCredits(c))
        issue('invalid-course','total','A course has an invalid category, status or credit value.','error',[c.id]);
      if(c.usedForBSc&&c.creditApproved!==false&&!['extra','requirement','scientific'].includes(c.role)&&c.status!=='interested')
        issue('bachelor-reuse',c.role==='specialisation'?'spec':c.role,'Credits already used for a Bachelor degree cannot count again.','error',[c.id]);
    }
    for(const c of courses.filter(credited)) {
      if(courses.some(other=>other.role==='requirement'&&other.status!=='interested'&&number(c)&&number(other)===number(c)))
        issue('admission-reuse','total','A module allocated as an admission requirement cannot also yield MSc credits.','error',[c.id]);
      if(courses.some(other=>other.usedForBSc&&number(c)&&number(other)===number(c)))
        issue('bachelor-reuse','total','A module already used for a Bachelor degree cannot yield MSc credits.','error',[c.id]);
    }
    const allocations=new Map();
    for(const c of courses.filter(credited)) {
      const key=allocationKey(c,courses);
      if(!allocations.has(key))allocations.set(key,[]);
      allocations.get(key).push(c);
    }
    for(const group of allocations.values())if(group.length>1)
      issue('duplicate-credit','total','The same module is allocated more than once; its credits count once.','error',group.map(c=>c.id));
    const sum=xs=>xs.reduce((total,c)=>total+c.ects,0);
    const rows=limits.map(rule=>{
      const key=rule.id;
      const select=kind=>{
        const active=unique.filter(c=>kind!=='completed'||c.status==='completed');
        let selected=key==='total'?active:key==='main'?active.filter(c=>['core','specialisation','elective'].includes(c.role)):
          active.filter(c=>c.role===(key==='spec'?'specialisation':key));
        if(key==='scientific')selected=courses.filter(c=>c.role==='scientific'&&c.status==='completed'&&c.creditApproved!==false);
        const metrics={ects:key==='scientific'?0:sum(selected),count:selected.length,
          lectures:selected.filter(c=>c.role==='specialisation'&&c.subtype!=='seminar').length,
          seminars:selected.filter(c=>c.role==='specialisation'&&c.subtype==='seminar').length,
          numbers:selected.map(number),courseIds:selected.map(c=>c.id)};
        if(key==='scientific'&&scientificWorksBSc)metrics.count=1;
        const reasons=[];
        if(metrics.ects+1e-8<rule.minEcts)reasons.push('credits');
        for(const [min,max,metric] of [['minCourses','maxCourses','count'],['minLectures','maxLectures','lectures'],['minSeminars','maxSeminars','seminars']]) {
          if(rule[min]!=null&&metrics[metric]<rule[min])reasons.push(min);
          if(rule[max]!=null&&metrics[metric]>rule[max])reasons.push(max);
        }
        if(rule.courseEcts!=null&&selected.some(c=>Math.abs(c.ects-rule.courseEcts)>1e-8))reasons.push('courseEcts');
        if(key==='core')for(const exclusion of rules.coreExclusions||[{numbers:['252-0535-00L','263-5210-00L'],maxCoreCreditsCourses:1}]) {
          if(metrics.numbers.filter(n=>exclusion.numbers.includes(n)).length>(exclusion.maxCoreCreditsCourses??1))reasons.push('core-exclusion');
        }
        return {...metrics,ok:reasons.length===0,reasons};
      };
      const planned=select('all'),completed=select('completed');
      for(const reason of planned.reasons)issue(reason,key,{
        credits:`Insufficient credits in ${key}.`,minCourses:`Too few courses in ${key}.`,maxCourses:`Too many courses allocated to ${key}; move surplus courses to an eligible category or attend-only.`,
        minLectures:'Too few specialisation lectures.',maxLectures:'Only four lectures can be allocated to the specialisation requirement.',
        minSeminars:'A specialisation seminar is missing.',maxSeminars:'Only one seminar can be allocated to the specialisation requirement.',
        courseEcts:`A course in ${key} has an unexpected credit value.`, 'core-exclusion':'AML and PAI cannot both count as core courses.'
      }[reason]);
      if(rule.warningEcts!=null&&planned.ects>rule.warningEcts+1e-8)
        issue('transcript-limit',key,`More than ${rule.warningEcts} ECTS are planned. Select the credits to include in the degree transcript; surplus study is allowed.`,'warning');
      return {key,target:rule.minEcts,planned:planned.ects,completed:completed.ects,courses:planned.count,
        potential:planned.ok,done:completed.ok,details:planned,completedDetails:completed,rule};
    });
    const fields=new Set(courses.filter(c=>c.role==='specialisation'&&credited(c)&&c.specialisation).map(c=>c.specialisation));
    if(fields.size>1)issue('field-review','spec','Courses span multiple specialisation fields; confirm the applicable major/minor rules for your Bachelor background.','warning');
    const needs=courses.filter(c=>c.role==='requirement'&&c.status!=='interested');
    const admission={courses:needs,done:needs.filter(c=>c.status==='completed').length};
    if(admission.done<needs.length)issue('admission-open','admission','Personal admission requirements are still open.');
    if(courses.some(c=>c.role==='specialisation'&&credited(c)&&!c.specialisation))
      issue('field-unverified','spec','Specialisation field eligibility still needs confirmation.','warning');
    const structural=issues.some(i=>['duplicate-credit','invalid-course','bachelor-reuse','admission-reuse'].includes(i.code));
    const plannedValid=rows.every(r=>r.potential)&&!structural&&admission.done===needs.length;
    const completedValid=rows.every(r=>r.done)&&!structural&&admission.done===needs.length;
    return {rows,issues,admission,plannedValid,completedValid,courses,credited:unique};
  }

  function moduleGrade(entry) {
    const parts=entry?.parts;
    if(!Array.isArray(parts)||!parts.length)return null;
    if(parts.some(p=>typeof p.value!=='number'||!Number.isFinite(p.value)||p.value<1||p.value>6||
      typeof p.weight!=='number'||!Number.isFinite(p.weight)||p.weight<=0))return null;
    const weight=parts.reduce((s,p)=>s+p.weight,0);
    if(!Number.isFinite(weight))return null;
    return parts.reduce((s,p)=>s+p.value*(p.weight/weight),0);
  }
  function calculateFinalGrade(entries,rules={}) {
    const weights={core:rules.gradeWeights?.coreCourse??2,specialisation:rules.gradeWeights?.specialisationLecture??1,
      elective:rules.gradeWeights?.elective??1,thesis:rules.gradeWeights?.masterThesis??4};
    const relevant=(Array.isArray(entries)?entries:[]).filter(e=>e&&typeof e==='object'&&e.countsForFinal!==false&&Object.hasOwn(weights,e.category)&&!(e.category==='specialisation'&&e.subtype==='seminar'));
    const counts=Object.fromEntries(Object.keys(weights).map(k=>[k,relevant.filter(e=>e.category===k).length]));
    const invalid=relevant.some(e=>moduleGrade(e)===null||moduleGrade(e)<4||e.usedForBSc===true);
    const seen=new Set();let duplicate=false;
    for(const e of relevant){const key=number(e)||e.courseId||String(e.name||'').trim().replace(/\s+/g,' ').toLowerCase();if(key){if(seen.has(key))duplicate=true;seen.add(key);}}
    const coreNumbers=relevant.filter(e=>e.category==='core').map(number);
    const conflict=(rules.coreExclusions||[{numbers:['252-0535-00L','263-5210-00L'],maxCoreCreditsCourses:1}]).some(x=>coreNumbers.filter(n=>x.numbers.includes(n)).length>(x.maxCoreCreditsCourses??1));
    const config=rules.gradeFormula||{};
    const complete=!invalid&&!duplicate&&!conflict&&counts.core===(config.coreCourseCount??2)&&counts.specialisation===(config.specialisationLectureCount??4)&&
      counts.elective>=(config.electiveMinimumCount??2)&&counts.thesis===(config.masterThesisCount??1);
    const valid=relevant.filter(e=>moduleGrade(e)!==null);
    const denominator=valid.reduce((s,e)=>s+weights[e.category],0);
    const value=denominator?valid.reduce((s,e)=>s+moduleGrade(e)*weights[e.category],0)/denominator:null;
    return {counts,complete,denominator,value:complete?value:null,invalid,duplicate,conflict};
  }

  function matchesInterest(c,i){
    return number(i)?number(c)===number(i):c.interestId?c.interestId===i.id:c.id===i.id||(!number(c)&&c.title?.trim().toLowerCase()===i.title?.trim().toLowerCase());
  }
  function availableShortlist(state,planId){
    const plan=[state.actualPlan,...state.plans].find(p=>p.id===planId);
    if(!plan)return [];
    const assigned=allCourses(plan,state.history||[]);
    return state.interests.filter(i=>!assigned.some(c=>matchesInterest(c,i)));
  }
  function confirmedOffering(c,term){
    if(c.offerings?.[term])return c.offerings[term];
    if(c.unitId&&c.sourceSemester===term)return c.unitId;
    if(c.unitId||Object.keys(c.offerings||{}).length)throw Error('Kein bestätigtes Angebot im Zielsemester / No confirmed offering in target semester.');
    return null;
  }
  function assignShortlist(state,planId,term,ids,role,idFactory){
    const plan=[state.actualPlan,...state.plans].find(p=>p.id===planId);
    if(!plan||!/^\d{4}[SW]$/.test(term)||!ids.length||new Set(ids).size!==ids.length)throw Error('Bitte Module und Zielsemester auswählen / Select modules and target semester.');
    if(plan.lockedSemesters.includes(term))throw Error('Semester ist gesperrt / Semester is locked.');
    const available=availableShortlist(state,planId);
    const records=ids.map(key=>{
      const i=available.find(i=>i.id===key);
      if(!i)throw Error('Modul bereits zugewiesen oder nicht verfügbar / Module already assigned or unavailable.');
      const unit=confirmedOffering(i,term),category=role==='suggested'?(i.suggestedRole||'elective'):role;
      if(!roles.includes(category))throw Error('Ungültige Kategorie / Invalid category.');
      return {id:idFactory(),interestId:i.id,number:i.number||'',title:i.title,ects:i.ects||0,semester:term,role:category,status:'planned',
        unitId:unit,sourceSemester:unit?term:null,offerings:i.offerings||{},proxy:false,events:[],locked:false,reviewAvailable:!!i.reviewAvailable,creditApproved:category==='extra'?false:null};
    });
    if(records.some((c,index)=>records.slice(0,index).some(other=>matchesInterest(other,{...c,id:c.interestId}))))throw Error('Doppelte Module in Auswahl / Duplicate modules in selection.');
    if(!plan.semesters.includes(term)){plan.semesters.push(term);plan.semesters.sort();}
    plan.courses.push(...records);
  }
  function moveAllocation(state,fromId,courseId,toId,term,role){
    const plans=[state.actualPlan,...state.plans],from=plans.find(p=>p.id===fromId),to=plans.find(p=>p.id===toId),c=from?.courses.find(c=>c.id===courseId);
    if(!c||!to||!/^\d{4}[SW]$/.test(term))throw Error('Ungültiges Ziel / Invalid target.');
    if(c.locked||from.lockedSemesters.includes(c.semester)||to.lockedSemesters.includes(term))throw Error('Kurs oder Semester ist gesperrt / Course or semester is locked.');
    const unit=confirmedOffering(c,term);
    if(to.courses.some(x=>!(from===to&&x.id===c.id)&&matchesInterest(x,{...c,id:c.interestId||c.id})))throw Error('Modul im Zielplan bereits zugewiesen / Module already assigned in target plan.');
    if(role&&!roles.includes(role))throw Error('Ungültige Kategorie / Invalid category.');
    const record={...c,role:role||c.role,semester:term,events:term===c.semester?c.events:[],unitId:unit,sourceSemester:unit?term:null,proxy:false};
    from.courses=from.courses.filter(x=>x.id!==c.id);
    if(!to.semesters.includes(term)){to.semesters.push(term);to.semesters.sort();}
    to.courses.push(record);
  }
  const api={matchesInterest,availableShortlist,confirmedOffering,assignShortlist,moveAllocation,credited,allCourses,uniqueCredits,audit,moduleGrade,calculateFinalGrade};
  root.MasterPlanRules=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
