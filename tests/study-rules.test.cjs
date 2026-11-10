'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const R=require('../web/study-rules.js');
const rules=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../guidelines/cse-guidelines.json')));
let serial=0;
function course(role,ects=6,patch={}) {return {id:`c${++serial}`,number:`TEST-${serial}`,title:`Test ${serial}`,role,ects,status:'planned',semester:'2026W',events:[],...patch};}
function fixture(status='planned') {
  return {id:'actual',name:'Synthetic audit fixture',specialisation:'Physics',semesters:['2026W','2027S'],lockedSemesters:[],courses:[
    course('core',6),course('core',6),...Array.from({length:4},()=>course('specialisation',4,{subtype:'lecture',specialisation:'Physics'})),
    course('specialisation',2,{subtype:'seminar',specialisation:'Physics'}),course('elective',22),course('elective',22),
    course('case',3,{number:'CASE-STUDIES',semester:'2026W'}),course('case',3,{number:'CASE-STUDIES',semester:'2027S'}),
    course('project',8),course('sip',2),course('thesis',30),course('scientific',0,{status:'completed'})
  ].map(c=>({...c,status:c.role==='scientific'?'completed':status}))};
}
const audit=(p,history=[],config=rules,bsc=false)=>R.audit(p,history,config,bsc);
const row=(a,key)=>a.rows.find(r=>r.key===key);
const codes=a=>a.issues.map(i=>i.code);

test('valid 120-ECTS fixture distinguishes planned and completed achievements',()=>{
  let a=audit(fixture());assert.equal(a.plannedValid,true);assert.equal(a.completedValid,false);assert.equal(row(a,'total').planned,120);
  a=audit(fixture('completed'));assert.equal(a.completedValid,true);assert.equal(a.issues.length,0);
});
for(const [role,key] of [['core','core'],['specialisation','spec'],['case','case'],['project','project'],['sip','sip'],['thesis','thesis'],['scientific','scientific']])
  test(`missing ${role} cannot be replaced by extra electives`,()=>{
    const p=fixture();p.courses=p.courses.filter(c=>c.role!==role);
    p.courses.push(...Array.from({length:8},()=>course('elective',15)));
    const a=audit(p);assert.equal(row(a,key).potential,false);assert.equal(a.plannedValid,false);
    assert.equal(row(a,'elective').potential,true);assert.equal(row(a,'total').potential,true);
  });
for(const count of [0,1,3,4])test(`${count} core courses is invalid even with sufficient credits`,()=>{
  const p=fixture();p.courses=p.courses.filter(c=>c.role!=='core');
  p.courses.push(...Array.from({length:count},()=>course('core',18)));
  assert.equal(row(audit(p),'core').potential,false);
});
test('two cores with insufficient combined credits stay open',()=>{
  const p=fixture();p.courses.filter(c=>c.role==='core').forEach(c=>c.ects=5.5);
  assert.equal(row(audit(p),'core').potential,false);
});
test('AML and PAI cannot both count as cores, but one may be an elective',()=>{
  const p=fixture();const core=p.courses.filter(c=>c.role==='core');core[0].number='252-0535-00L';core[1].number='263-5210-00L';
  assert.ok(codes(audit(p)).includes('core-exclusion'));
  core[1].role='elective';p.courses.push(course('core',6));assert.equal(row(audit(p),'core').potential,true);
});
for(const [lectures,seminars] of [[3,1],[4,0],[5,0],[3,2],[5,1],[4,2],[0,5]])
  test(`${lectures} specialisation lectures and ${seminars} seminars do not satisfy four-plus-one`,()=>{
    const p=fixture();p.courses=p.courses.filter(c=>c.role!=='specialisation');
    p.courses.push(...Array.from({length:lectures},()=>course('specialisation',6,{subtype:'lecture'})),...Array.from({length:seminars},()=>course('specialisation',6,{subtype:'seminar'})));
    assert.equal(row(audit(p),'spec').potential,false);
  });
test('correct specialisation count still needs eighteen credits',()=>{
  const p=fixture();p.courses.filter(c=>c.role==='specialisation').forEach(c=>c.ects=3);
  assert.equal(row(audit(p),'spec').potential,false);
});
test('one large elective does not satisfy the two-course minimum',()=>{
  const p=fixture();p.courses=p.courses.filter(c=>c.role!=='elective');p.courses.push(course('elective',40));
  assert.equal(row(audit(p),'elective').potential,false);
});
for(const ects of [120,129.999,130,130.001,160,400])test(`${ects} total ECTS: 130 ceiling is warning-only`,()=>{
  const p=fixture('completed');let extra=ects-120;
  while(extra>1e-8){const amount=Math.min(40,extra);p.courses.push(course('elective',amount,{status:'completed'}));extra-=amount;}
  const a=audit(p);assert.equal(a.completedValid,true);assert.equal(row(a,'total').planned,ects);
  assert.equal(a.issues.some(i=>i.code==='transcript-limit'),ects>130+1e-8);
  assert.ok(a.issues.filter(i=>i.code==='transcript-limit').every(i=>i.severity==='warning'));
});
test('distinct category credit minima and main-area minimum are independent',()=>{
  const p=fixture();p.courses.filter(c=>c.role==='elective').forEach(c=>c.ects=6);
  p.courses.push(course('sip',32));const a=audit(p);
  assert.equal(row(a,'total').potential,true);assert.equal(row(a,'main').potential,false);assert.equal(row(a,'elective').potential,true);
});
for(const role of ['extra','requirement','scientific'])test(`${role} credits never count towards the MSc`,()=>{
  const p=fixture();p.courses.push(course(role,40,{status:'completed'}));assert.equal(row(audit(p),'total').planned,120);
});
for(const patch of [{creditApproved:false},{usedForBSc:true},{status:'interested'},{ects:0}])
  test(`non-credit course does not satisfy count or ECTS: ${JSON.stringify(patch)}`,()=>{
    const p=fixture();Object.assign(p.courses.find(c=>c.role==='core'),patch);
    assert.equal(row(audit(p),'core').potential,false);assert.equal(audit(p).plannedValid,false);
  });
test('scientific works is completed-only and may be satisfied by the Bachelor flag',()=>{
  const p=fixture();p.courses.find(c=>c.role==='scientific').status='planned';
  assert.equal(row(audit(p),'scientific').potential,false);assert.equal(row(audit(p,[],rules,true),'scientific').potential,true);
});
test('open admission conditions block completion, but contribute zero MSc credits',()=>{
  const p=fixture('completed');const need=course('requirement',9);p.courses.push(need);
  assert.equal(audit(p).completedValid,false);assert.equal(row(audit(p),'total').completed,120);
  need.status='completed';assert.equal(audit(p).completedValid,true);
});
test('duplicate modules across semesters and categories count once and are flagged',()=>{
  const p=fixture();const c=p.courses[0];p.courses.push({...c,id:'repeat',semester:'2027S',role:'elective'});
  const a=audit(p);assert.equal(row(a,'total').planned,120);assert.ok(codes(a).includes('duplicate-credit'));assert.equal(a.plannedValid,false);
});
test('normalized catalogue numbers cannot bypass duplicate detection',()=>{
  const p=fixture();p.courses[0].number='ABC-123';p.courses.push({...p.courses[0],id:'repeat',number:' abc-123 ',semester:'2027S'});
  assert.equal(row(audit(p),'total').planned,120);assert.ok(codes(audit(p)).includes('duplicate-credit'));
});
test('case studies may repeat the same module in different semesters',()=>{
  const p=fixture();const a=audit(p);assert.equal(row(a,'case').courses,2);assert.equal(row(a,'case').potential,true);assert.ok(!codes(a).includes('duplicate-credit'));
  p.courses.filter(c=>c.role==='case')[1].semester='2026W';assert.equal(row(audit(p),'case').potential,false);assert.ok(codes(audit(p)).includes('duplicate-credit'));
});
test('a core cannot be double-counted by relabelling its duplicate as a case study',()=>{
  const p=fixture();p.courses.push({...p.courses[0],id:'fake-case',role:'case',ects:3});const a=audit(p);
  assert.ok(codes(a).includes('duplicate-credit'));assert.equal(row(a,'total').planned,120);
});
test('case-study entries with 1 and 5 credits cannot mimic two real three-credit participations',()=>{
  const p=fixture();const cases=p.courses.filter(c=>c.role==='case');cases[0].ects=1;cases[1].ects=5;
  assert.equal(row(audit(p),'case').potential,false);
});
test('additional semester projects need elective allocation',()=>{
  const p=fixture();const extra=course('project',8);p.courses.push(extra);assert.equal(row(audit(p),'project').potential,false);
  extra.role='elective';assert.equal(row(audit(p),'project').potential,true);assert.equal(audit(p).plannedValid,true);
});
test('history supplies completed status without overriding scenario category or exclusion',()=>{
  const p=fixture();const c=p.courses[0];const history=[{...c,role:'elective',status:'completed'}];
  assert.equal(R.allCourses(p,history).find(x=>x.id===c.id).role,'core');assert.equal(row(audit(p,history),'core').completed,6);
  c.role='extra';assert.equal(row(audit(p,history),'core').completed,0);assert.equal(row(audit(p,history),'total').planned,114);
});
test('history does not duplicate a module already in the plan',()=>{
  const p=fixture('completed');assert.equal(row(audit(p,p.courses),'total').completed,120);assert.equal(audit(p,p.courses).completedValid,true);
});
for(const value of [-1,NaN,Infinity,'6',null,41])test(`invalid ECTS ${String(value)} cannot complete requirements`,()=>{
  const p=fixture();p.courses[0].ects=value;const a=audit(p);assert.equal(a.plannedValid,false);assert.ok(codes(a).includes('invalid-course'));
});
test('guideline count overrides and core exclusions are actually read',()=>{
  const p=fixture();const config=structuredClone(rules);config.requirements.find(x=>x.id==='core').minCourses=3;config.requirements.find(x=>x.id==='core').maxCourses=3;
  assert.equal(row(audit(p,[],config),'core').potential,false);p.courses.push(course('core',6));assert.equal(row(audit(p,[],config),'core').potential,true);
});
// Independent expected counts/credit arithmetic: 5*7*3*7 = 735 allocations.
test('735 combinations of core, lecture, seminar and elective counts',()=>{
  let tested=0;
  for(let cores=0;cores<=4;cores++)for(let lectures=0;lectures<=6;lectures++)for(let seminars=0;seminars<=2;seminars++)for(let electives=0;electives<=6;electives++){
    const p=fixture();p.courses=p.courses.filter(c=>!['core','specialisation','elective'].includes(c.role));
    p.courses.push(...Array.from({length:cores},()=>course('core',6)),...Array.from({length:lectures},()=>course('specialisation',4,{subtype:'lecture'})),
      ...Array.from({length:seminars},()=>course('specialisation',2,{subtype:'seminar'})),...Array.from({length:electives},()=>course('elective',8)));
    const a=audit(p),main=cores*6+lectures*4+seminars*2+electives*8;
    const expected=cores===2&&lectures===4&&seminars===1&&electives>=2&&main>=74&&main+46>=120;
    assert.equal(row(a,'core').potential,cores===2,JSON.stringify({cores,lectures,seminars,electives}));
    assert.equal(row(a,'spec').potential,lectures===4&&seminars===1);
    assert.equal(row(a,'elective').potential,electives>=2);
    assert.equal(row(a,'main').potential,main>=74);
    assert.equal(row(a,'total').planned,main+46);
    assert.equal(a.plannedValid,expected);tested++;
  }
  assert.equal(tested,735);
});

function grades(){return ['core','core',...Array(4).fill('specialisation'),'elective','elective','thesis'].map(category=>({category,parts:[{value:5,weight:100}]}));}
test('grade uses category weights and includes all valid electives',()=>{
  const g=grades();g[0].parts[0].value=4;g.at(-1).parts[0].value=6;
  let a=R.calculateFinalGrade(g,rules);assert.equal(a.complete,true);assert.equal(a.denominator,14);assert.equal(a.value,72/14);
  g.push({category:'elective',parts:[{value:4,weight:100}]});a=R.calculateFinalGrade(g,rules);assert.equal(a.complete,true);assert.equal(a.denominator,15);assert.equal(a.value,76/15);
});
for(const key of ['core','specialisation','elective','thesis'])test(`missing ${key} grade does not show a final average`,()=>{
  const g=grades();g.splice(g.findIndex(e=>e.category===key),1);const a=R.calculateFinalGrade(g,rules);assert.equal(a.complete,false);assert.equal(a.value,null);
});
for(const key of ['core','specialisation','thesis'])test(`surplus ${key} grade makes final selection incomplete`,()=>{
  const g=grades();g.push({category:key,parts:[{value:5,weight:100}]});assert.equal(R.calculateFinalGrade(g,rules).complete,false);
});
for(const parts of [[],[{value:0,weight:100}],[{value:7,weight:100}],[{value:NaN,weight:100}],[{value:5,weight:0}],[{value:5,weight:-1}],[{value:5,weight:Infinity}],[{value:'5',weight:100}]])
  test(`malformed grade components ${JSON.stringify(parts)} cannot produce a final grade`,()=>{
    const g=grades();g[0].parts=parts;assert.equal(R.moduleGrade(g[0]),null);assert.equal(R.calculateFinalGrade(g,rules).complete,false);
  });
test('seminars and non-final categories do not enter the grade formula',()=>{
  const g=grades();g.push({category:'specialisation',subtype:'seminar',parts:[{value:1,weight:100}]},...['case','project','sip','scientific','extra','requirement'].map(category=>({category,parts:[{value:1,weight:100}]})));
  assert.equal(R.calculateFinalGrade(g,rules).value,5);
});
test('duplicate modules, Bachelor reuse and AML/PAI are rejected in final-grade selection',()=>{
  let g=grades();g[0].number='DUPLICATE';g[1].number='duplicate';assert.equal(R.calculateFinalGrade(g,rules).complete,false);
  g=grades();g[0].usedForBSc=true;assert.equal(R.calculateFinalGrade(g,rules).complete,false);
  g=grades();g[0].number='252-0535-00L';g[1].number='263-5210-00L';assert.equal(R.calculateFinalGrade(g,rules).complete,false);
});
test('module component grades are normalized by their weights',()=>assert.equal(R.moduleGrade({parts:[{value:4,weight:25},{value:6,weight:75}]}),5.5));

test('a failed counted module blocks a final grade even if the overall average would pass',()=>{
  for(const value of [1,3,3.99]){const g=grades();g[0].parts[0].value=value;assert.equal(R.calculateFinalGrade(g,rules).complete,false);assert.equal(R.calculateFinalGrade(g,rules).value,null);}
});
test('a failing component is allowed when the weighted module grade passes',()=>{
  const g=grades();g[0].parts=[{value:3,weight:25},{value:5,weight:75}];assert.equal(R.calculateFinalGrade(g,rules).complete,true);
});
test('a manually repeated module name cannot count twice in grade selection',()=>{
  const g=grades();g[0].name='Repeated Module';g[1].name=' repeated   module ';assert.equal(R.calculateFinalGrade(g,rules).complete,false);
});
test('admission credits cannot be reused in a separate MSc record',()=>{
  const p=fixture();p.courses.push({...p.courses[0],id:'admission',role:'requirement',status:'completed'});
  const a=audit(p);assert.ok(codes(a).includes('admission-reuse'));assert.equal(row(a,'total').planned,114);assert.equal(a.plannedValid,false);
});
test('Bachelor reuse in history also excludes the same course in a scenario',()=>{
  const p=fixture();const history=[{...p.courses[0],usedForBSc:true,status:'completed'}];
  assert.equal(row(audit(p,history),'total').planned,114);assert.equal(audit(p,history).plannedValid,false);
});
test('same-title manual courses with different IDs are not silently conflated',()=>{
  const p=fixture();p.courses.filter(c=>c.role==='core').forEach(c=>{c.number='';c.title='Manually verified core';});
  assert.equal(row(audit(p),'core').potential,true);
});

test('audit leaves plans, shared history and guideline configuration unchanged',()=>{
  const p=fixture('completed'),history=structuredClone(p.courses),before=JSON.stringify({p,history,rules});audit(p,history);
  assert.equal(JSON.stringify({p,history,rules}),before);
});
test('256 status combinations keep planned and completed requirements distinct',()=>{
  const statuses=['interested','planned','enrolled','completed'];let count=0;
  for(const core of statuses)for(const spec of statuses)for(const elective of statuses)for(const thesis of statuses){
    const p=fixture('completed'),chosen={core,specialisation:spec,elective,thesis};
    p.courses.forEach(c=>{if(chosen[c.role])c.status=chosen[c.role];});
    const a=audit(p);
    for(const [role,key] of [['core','core'],['specialisation','spec'],['elective','elective'],['thesis','thesis']]){
      assert.equal(row(a,key).done,chosen[role]==='completed');assert.equal(row(a,key).potential,chosen[role]!=='interested');
    }
    assert.equal(a.completedValid,Object.values(chosen).every(s=>s==='completed'));count++;
  }
  assert.equal(count,256);
});
test('360 final-grade category-count combinations follow the two/four/two-plus/one rule',()=>{
  let checked=0;
  for(let core=0;core<=3;core++)for(let spec=0;spec<=5;spec++)for(let elective=0;elective<=4;elective++)for(let thesis=0;thesis<=2;thesis++){
    const g=Object.entries({core,specialisation:spec,elective,thesis}).flatMap(([category,count])=>Array.from({length:count},()=>({category,parts:[{value:5,weight:100}]})));
    const a=R.calculateFinalGrade(g,rules),expected=core===2&&spec===4&&elective>=2&&thesis===1;
    assert.equal(a.complete,expected);assert.equal(a.value,expected?5:null);checked++;
  }
  assert.equal(checked,360);
});
