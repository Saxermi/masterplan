const $ = s => document.querySelector(s);
const escape = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const attrs = x => escape(x).replace(/`/g,'&#96;');
const id = () => globalThis.crypto?.randomUUID?.() || `id-${Date.now()}-${Math.random().toString(36).slice(2)}`;
const programmes = {'cse':'MSc CSE','eligible-core-all':'Alle MSc-Core-Optionen (CSE) / All MSc core options (CSE)','cse-bsc':'RW / CSE Bachelor (Auflagen)','mathematics-bsc':'Mathematics BSc','mathematics-msc':'Mathematics MSc (auch Applied Mathematics)','applied-mathematics-msc':'Applied Mathematics MSc (VVZ: Mathematics)','physics-bsc':'Physics BSc','physics-msc':'Physics MSc','computer-science-msc':'Computer Science MSc','statistics-msc':'Statistics MSc','data-science-msc':'Data Science MSc','neural-systems-msc':'Neural Systems and Computation MSc','robotics-msc':'Robotics, Systems and Control MSc','electrical-engineering-msc':'Electrical Engineering and Information Technology MSc','all':'All ETH / Alle ETH'};
const eligibleCoreProgrammes = ['mathematics-msc','applied-mathematics-msc','physics-msc','computer-science-msc','statistics-msc','data-science-msc','neural-systems-msc','robotics-msc','electrical-engineering-msc'];
const eligibleCoreSelection = key => key === 'eligible-core-all' || (guidelines?.electiveEligibility?.coreCourseProgrammeKeys || eligibleCoreProgrammes).includes(key);
const specialisations = ['Astrophysics','Biology','Chemistry','Computational Finance','Electromagnetics','Fluid Dynamics','Geophysics','Physics','Physics of the Atmosphere','Robotics','Systems and Control'];
const roleList = ['core','specialisation','specialisation-seminar','elective','case','project','sip','thesis','scientific','extra','requirement'];
const roles = {core:['Core Course','Core Course'],specialisation:['Spezialisierungsvorlesung','Specialisation lecture'],'specialisation-seminar':['Spezialisierungsseminar','Specialisation seminar'],elective:['Elective','Elective'],case:['Case Study','Case study'],project:['Semesterprojekt','Semester project'],sip:['Science in Perspective','Science in Perspective'],thesis:['Masterarbeit','Master thesis'],scientific:['Scientific Works (0 ECTS)','Scientific Works (0 ECTS)'],extra:['Nur besuchen · 0 ECTS','Attend only · 0 ECTS'],requirement:['Zulassungsauflage','Additional requirement']};
const navItems = [['dashboard','⌂','Übersicht','Dashboard'],['schedule','▦','Stundenplan','Timetable'],['semesters','▤','Semesterplanung','Semester planning'],['plans','▧','Studienpläne','Study plans'],['catalog','⌕','Modulkatalog','Course catalogue'],['requirements','✓','Studienregeln','Requirements'],['grades','∑','Noten (separat)','Grades (private)'],['simulation','◇','Studiensimulation','Study simulation'],['settings','⚙','Einstellungen','Settings']];
const tr = (de,en) => state.language === 'en' ? en : de;
const trRole = r => (roles[r] || roles.extra)[state.language === 'en' ? 1 : 0];
const semName = x => x ? `${x.endsWith('S')?'FS':'HS'} ${x.slice(0,4)}` : '—';
function recentTerms() {
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Zurich',year:'numeric',month:'2-digit'}).formatToParts(new Date());
  const year=Number(parts.find(x=>x.type==='year').value),month=Number(parts.find(x=>x.type==='month').value);
  const terms=[];for(let y=year-3;y<=year+2;y++)terms.push(`${y}S`,`${y}W`);
  const current=`${month===1?year-1:year}${month===1||month>=9?'W':'S'}`;
  return terms.slice(terms.indexOf(current)-2,terms.indexOf(current)+3);
}
const formatNum = x => Number(x||0).toLocaleString(state.language==='en'?'en-GB':'de-CH',{maximumFractionDigits:1});
const safe = x => Number.isFinite(Number(x)) ? Number(x) : 0;
const allPlans = () => [state.actualPlan,...state.plans];
const getPlan = key => allPlans().find(p=>p.id===key) || state.actualPlan;
const plan = () => getPlan(state.activePlan);
const actual = () => state.actualPlan;
const editPlan = (s,key) => key==='actual' ? s.actualPlan : s.plans.find(p=>p.id===key);
const classify = c => c.role === 'extra' ? 'orange' : c.role === 'requirement' ? 'gray' : '';
const credited = c => MasterPlanRules.credited(c);
const officialVvzUrl = c => c.unitId && /^\d{4}[SW]$/.test(c.sourceSemester||c.semester||'') ? `https://www.vvz.ethz.ch/Vorlesungsverzeichnis/lerneinheit.view?lerneinheitId=${encodeURIComponent(c.unitId)}&semkez=${encodeURIComponent(c.sourceSemester||c.semester)}&lang=${state.language}` : c.number && /^[A-Za-z0-9-]{5,35}$/.test(c.number) ? `https://www.vvz.ethz.ch/Vorlesungsverzeichnis/sucheLehrangebot.view?lerneinheitscode=${encodeURIComponent(c.number)}&semkez=${encodeURIComponent(c.semester||recentTerms()[2])}&lang=${state.language}` : null;
const reviewUrl = c => c.reviewAvailable && /^[A-Za-z0-9-]{5,35}$/.test(c.number||'') ? `https://coursereview.ch/course/${encodeURIComponent(c.number)}` : null;
function courseLinks(c){const links=[];const vvz=officialVvzUrl(c)||`https://www.vvz.ethz.ch/Vorlesungsverzeichnis/sucheLehrangebotPre.view?semkez=${encodeURIComponent(c.semester||recentTerms()[2])}&lang=${state.language}`;if(vvz)links.push(`<a href="${attrs(vvz)}" target="_blank" rel="noopener noreferrer">${tr('ETH-Vorlesungsverzeichnis','ETH course catalogue')} ↗</a>`);const rev=reviewUrl(c);if(rev)links.push(`<a href="${attrs(rev)}" target="_blank" rel="noopener noreferrer">CourseReview ↗</a>`);return links.length?`<div class="course-links">${links.join(' ')}</div>`:'';}
const meetingData = new Map();
let meetingTimer=null;
function offeringFor(semesters,target){return MasterPlanRules.resolveOffering({offerings:semesters},target);}
async function syncMeetingOptions(){if(page!=='schedule')return;const p=plan(),sem=schedule.current||p.semesters[0];let changed=false;for(const c of allCourses(p).filter(x=>x.semester===sem&&x.unitId)){const k=String(c.unitId),entry=meetingData.get(k);if((entry?.status==='failed'||entry?.status==='ready'&&['ready','failed'].includes(entry.groupStatus))&&Date.now()-(entry.polledAt||0)<60000)continue;try{const x=await request('/api/vvz/times/'+encodeURIComponent(k));if(x.status==='ready'){const oldKeys=entry?.meetings?.map(m=>m.slotKey).join(',');const newKeys=(x.meetings||[]).map(m=>m.slotKey).join(',');const updated=!!entry&&oldKeys!==newKeys;meetingData.set(k,{status:'ready',meetings:x.meetings||[],source:x.source,groupStatus:x.groupStatus||'queued',error:x.error||null,polledAt:Date.now(),changed:updated||entry?.changed});if(updated&&entry?.groupStatus==='ready')notify(tr('VVZ-Termine haben sich geändert. Bitte Auswahl überprüfen.','VVZ meetings changed. Please review your selections.'));changed=true;}else if(!entry)meetingData.set(k,{status:'queued',polledAt:Date.now()});}catch(e){meetingData.set(k,{status:'failed',error:e.message,polledAt:Date.now()});changed=true;}}if(changed&&page==='schedule')render();}
function beginMeetingSync(){if(meetingTimer)clearInterval(meetingTimer);meetingTimer=null;if(page==='schedule'){meetingTimer=setInterval(()=>{if(page==='schedule')void syncMeetingOptions();},10000);void syncMeetingOptions();}}

let guidelines = null;
let comparisonView = 'plans', comparison = {leftPlan:null,leftSemester:null,rightPlan:null,rightSemester:null};
let dumpStatus = null, dumpStatusTimer = null;
let state, page = 'dashboard', results = [], searchParams = {q:'',programme:'cse',category:'core',semester:recentTerms()[2]}, searchState = '', gradesCache = null, gradesPassword = null;

async function request(url, method='GET', data=null) {
  const options = {method, headers:{}};
  if (data!==null) {options.headers['Content-Type']='application/json';options.body=JSON.stringify(data);}
  let res;
  try { res=await fetch(url, options); } catch { throw new Error(tr('Server nicht erreichbar','Server unavailable')); }
  const payload=await res.json().catch(()=>({error:'Invalid server response'}));
  if (!res.ok) {const error=new Error(payload.error || `${res.status}`);error.status=res.status;throw error;}
  return payload;
}
function notify(s) {const x=$('#toast');x.textContent=s;x.classList.add('show');clearTimeout(notify.timer);notify.timer=setTimeout(()=>x.classList.remove('show'),4500);}
let saveQueue = Promise.resolve();
let searchGeneration = 0, catalogOffset = 0, catalogTotal = 0;
function save(mutator) {
  const operation = async () => {
    const draft=structuredClone(state);let succeeded=false;
    try {
      mutator(draft);
      updateStatus(tr('Speichert…','Saving…'));
      state=await request('/api/state','POST',draft);succeeded=true;
      updateStatus(tr('Lokal gespeichert','Saved locally'));
    } catch(err) {
      if(err.status===409) {
        try {state=await request('/api/state');} catch {}
        notify(tr('Anderer Speicherstand erkannt. Aktueller Stand geladen; bitte die letzte Änderung erneut durchführen.','Another saved version was detected. Latest version loaded; please repeat the last change.'));
      } else notify(err.message);
      updateStatus(tr('Speicherfehler','Save error'));
    }
    render();return succeeded;
  };
  saveQueue=saveQueue.then(operation,operation);
  return saveQueue;
}
async function runCatalogSearch(offset=0) {
  const generation=++searchGeneration;
  catalogOffset=offset;catalogTotal=0;results=[];
  if(searchParams.category==='specialisation'&&!state.selectedSpecialisations.length) {
    searchState=tr('Keine Spezialisierung ausgewählt.','No specialisations selected.');render();return;
  }
  searchState=tr('Suche läuft…','Searching…');render();
  try {
    const params=new URLSearchParams({...searchParams,offset,limit:40});
    if(searchParams.category==='specialisation')params.set('spec',state.selectedSpecialisations.join('|'));
    const data=await request('/api/vvz/search?'+params);
    if(generation!==searchGeneration)return;
    results=(data.results||[]).map(c=>({...c,eligibleCoreElective:!!data.eligibleCoreElective}));
    catalogTotal=data.total??results.length;
    searchState=`${catalogTotal} ${tr('Treffer','results')} · ${data.source}`;render();
  } catch(e) {
    if(generation!==searchGeneration)return;
    searchState=e.message;render();notify(e.message);
  }
}
function updateStatus(msg) {$('#save-status').textContent=msg;}
function changePage(next) {page=next;gradeDraft=null;if(!['grades','simulation'].includes(next)){gradesCache=null;gradesPassword=null;}$('#sidebar').classList.remove('open');render();if(next==='settings'){loadFolder();refreshDumpStatus();}}
function pill(text,type='') {return `<span class="pill ${type}">${escape(text)}</span>`;}
function button(text,action,extra='',cls='smallbtn'){return `<button class="${cls}" data-action="${action}" ${extra}>${text}</button>`;}
function pageHeader(title,desc,action='') {return `<div class="row between wrap" style="margin-bottom:22px"><div><h1 class="page-title">${title}</h1><p class="subtitle" style="margin-bottom:0">${desc}</p></div>${action}</div>`;}
let detailCourse=null,detailsBack='catalog';const unitDetailsCache=new Map();
function moduleTitle(c){
  const off=c.offering||{},unit=c.unitId||off.unit_id||null,term=c.sourceSemester||off.source_semester||c.semester||'';
  return button(escape(c.title||c.title_english||c.number||tr('Modul','Course')),'course-details',`data-unit-id="${attrs(unit||'')}" data-title="${attrs(c.title||c.title_english||c.number||'')}" data-number="${attrs(c.number||'')}" data-source-semester="${attrs(term)}"`,'course-title');
}
function courseDetails(){
  const entry=unitDetailsCache.get(String(detailCourse?.unitId)),unit=entry?.unit;
  const field=key=>state.language==='en'?(unit?.[key+'_english']||unit?.[key]):(unit?.[key]||unit?.[key+'_english']);
  return `${pageHeader(tr('Moduldetails','Course details'),escape(detailCourse?.title||''),button(tr('Zurück','Back'),'close-details'))}
    <div class="card"><h2>${escape(detailCourse?.title)}</h2><p>${escape(detailCourse?.number||'')} · ${semName(detailCourse?.sourceSemester)}</p>${courseLinks(detailCourse||{})}
    ${!detailCourse?.unitId?`<p>${tr('Keine VVZ-Kennung vorhanden. Details bitte im verlinkten Vorlesungsverzeichnis prüfen.','No VVZ unit ID is available. Please check the linked official catalogue.')}</p>`:entry?.error?`<p role="status">${escape(entry.error)}</p>${button(tr('Erneut laden','Retry'),'retry-details')}`:!unit?`<p role="status">${tr('Kursinformationen werden geladen…','Loading course information…')}</p>`:
      [['abstract',tr('Kursbeschreibung','Course description')],['objective',tr('Lernziele','Learning objectives')],['content',tr('Inhalte','Contents')],['literature',tr('Literatur','Literature')]].map(([key,label])=>`<section><h3>${label}</h3><p class="course-detail-text">${escape(field(key)||tr('Keine Angaben in den Kursdaten vorhanden.','No information supplied in the course data.'))}</p></section>`).join('')}</div>`;
}
async function loadCourseDetails(){const course=detailCourse;if(!course?.unitId)return;const key=String(course.unitId);if(!unitDetailsCache.has(key)){try{const result=await request('/api/vvz/unit/'+encodeURIComponent(key));if(!result.unit)throw Error(tr('Keine Kursdaten vorhanden.','No course data available.'));unitDetailsCache.set(key,{unit:result.unit});}catch(e){unitDetailsCache.set(key,{error:e.message});}}if(page==='course-details'&&detailCourse===course)render();}
function render() {
  document.documentElement.dataset.theme=state.theme;
  document.documentElement.lang=state.language;
  $('#lang-toggle').textContent=state.language.toUpperCase();
  $('#theme-toggle').textContent=state.theme==='dark'?'☀':'☾';
  $('#nav').innerHTML=navItems.map(([key,icon,de,en])=>`<button class="nav-item ${key===page?'active':''}" data-nav="${key}"><span>${icon}</span><span>${escape(tr(de,en))}</span></button>`).join('');
  $('#top-title').textContent=page==='course-details'?tr('Moduldetails','Course details'):(navItems.find(x=>x[0]===page)||navItems[0])[state.language==='en'?3:2];
  const renderers = {dashboard:dashboard,schedule:schedule,semesters:semesters,plans:plans,catalog:catalog,requirements:requirements,grades:grades,simulation:grades,settings:settings,'course-details':courseDetails};
  $('#app').innerHTML=(renderers[page]||dashboard)();

  refreshAssignmentChoices();
  if(page==='schedule' && !meetingTimer)beginMeetingSync();
  else if(page!=='schedule' && meetingTimer){clearInterval(meetingTimer);meetingTimer=null;}
}
function addSelect(options,value){return `<select data-change="active-plan" class="plan-select">${options.map(p=>`<option value="${attrs(p.id)}" ${p.id===value?'selected':''}>${escape(p.name)}</option>`).join('')}</select>`;}
function allCourses(p) {return MasterPlanRules.allCourses(p,state.history||[]);}
function studyAudit(p) {return MasterPlanRules.audit(p,state.history||[],guidelines||{},state.scientificWorksBSc);}
function courseTotal(p,mode='all') {return studyAudit(p).credited.filter(c=>mode==='all'||c.status==='completed').reduce((sum,c)=>sum+c.ects,0);}
function requirementRows(p) {
  const labels={main:tr('Main Areas (Core + Spezialisierung + Electives)','Main areas (core + specialisation + electives)'),core:'Core Courses',
    spec:tr('Spezialisierung (4 Vorlesungen + Seminar)','Specialisation (4 lectures + seminar)'),elective:'Electives',case:'Case Studies',
    project:tr('Semesterarbeit','Semester project'),sip:'Science in Perspective',thesis:tr('Masterarbeit','Master thesis'),
    total:tr('Gesamtabschluss','Total degree'),scientific:'Scientific Works (0 ECTS)'};
  return studyAudit(p).rows.map(r=>({...r,label:labels[r.key]}));
}
function bscRequirements(p) {return studyAudit(p).admission;}
function allocationIssues(p) {
  const audit=studyAudit(p);
  const warnings=audit.issues.filter(i=>!['credits','minCourses','minLectures','minSeminars'].includes(i.code));
  return `<div class="card spaced" id="allocation-audit"><h2 class="section-title">${tr('Zuordnungsprüfung','Allocation checks')}</h2>
    <p>${audit.plannedValid?tr('Die erfasste Planung erfüllt die geprüften Mindestanforderungen.','The recorded plan meets the checked requirements.'):tr('Die Planung ist noch unvollständig oder enthält ungültige Zuordnungen.','The plan is incomplete or has invalid allocations.')}</p>
    <p class="hint">${tr('Zusätzliche Electives ersetzen keine fehlenden Core-Kurse oder Spezialisierungsleistungen. Mehr als 130 ECTS sind erlaubt; der Hinweis betrifft nur die spätere Zeugnisauswahl.','Extra electives cannot replace missing core courses or specialisation achievements. More than 130 ECTS are allowed; the warning only concerns the later transcript selection.')}</p>
    ${warnings.map(i=>`<p class="note" data-audit-code="${attrs(i.code)}">${i.severity==='warning'?'⚠':'!'} ${escape(i.message)}</p>`).join('')}
    <p class="small muted">${tr('Auch eine vollständige rechnerische Planung benötigt die Prüfung der individuellen Anerkennung.','Even a numerically complete plan requires confirmation of individual eligibility.')}</p></div>`;
}

function requirementCard(r) {
  const progress=r.target?Math.min(100,100*r.completed/r.target):(r.done?100:0);
  const value=r.key==='scientific'?`${r.details.count}/1`: `${formatNum(r.completed)} / ${r.target}`;
  const details=r.key==='core'&&['252-0535-00L','263-5210-00L'].every(n=>r.details.numbers?.includes(n))?tr('AML und PAI dürfen nicht beide als Core Course zählen.','AML and PAI cannot both count as core courses.'):r.key==='spec'?`${r.details.lectures}/${r.rule.minLectures} ${tr('Vorlesungen','lectures')} · ${r.details.seminars}/${r.rule.minSeminars} Seminar`:
    r.key==='case'?`${r.courses}/${r.rule.minCourses} ${tr('Teilnahmen','sessions')}`:
    ['core','elective'].includes(r.key)?`${r.courses}/${r.rule.minCourses} ${r.rule.maxCourses===r.rule.minCourses?tr('Kurse (genau)','courses (exactly)'):tr('Kurse (mind.)','courses (min.)')}`:'';
  return `<div class="card compact" data-requirement="${attrs(r.key)}" data-potential="${r.potential}" data-done="${r.done}"><div class="row between"><strong class="small">${escape(r.label)}</strong>${pill(r.done?tr('Erfüllt','Completed'):r.potential?tr('Geplant','Planned'):tr('Offen','Open'),r.done?'green':r.potential?'':'orange')}</div>
    <div class="row between" style="margin-top:10px"><span class="small muted">${value}</span><span class="small muted">${r.key==='scientific'?'0 ECTS':`${formatNum(r.planned)} ECTS ${tr('inkl. Planung','incl. plan')}`}</span></div>
    <div class="progress" style="margin:10px 0 8px"><div style="width:${progress}%"></div></div>
    ${details?`<div class="tiny muted">${details}</div>`:''}</div>`;
}
function planSummary(p){const rows=requirementRows(p);return {ects:courseTotal(p),done:courseTotal(p,'completed'),open:rows.filter(x=>!x.potential).length,extras:allCourses(p).filter(x=>x.role==='extra').length};}
function programmeOptions(pls=allPlans(),chosen=state.activePlan){return `<select data-change="active-plan" class="plan-select">${pls.map(p=>`<option value="${attrs(p.id)}" ${p.id===chosen?'selected':''}>${escape(p.id==='actual'?tr('Tatsächliches Studium','Actual studies'):p.name)}</option>`).join('')}</select>`;}
function briefRequirements(p){return `<div class="grid columns-3">${requirementRows(p).map(requirementCard).join('')}</div>`;}
function selectedCourseCount(p){return p.courses.filter(c=>c.status!=='interested').length;}

function dashboard() {
  const p=actual(), info=planSummary(p), required=requirementRows(p), admission=bscRequirements(p);
  return `${pageHeader(tr('Mein tatsächliches Studium','My actual studies'),tr('Dein aktueller Stand – keine hypothetische Spezialisierung. Szenarien werden separat verglichen.','Your real progress – no hypothetical specialisation. Scenarios are compared separately.'),button(tr('Semesterplanung','Semester planning'),'go-semesters','','button'))}
    <div class="grid columns-4"><div class="card"><div class="label">${tr('Anrechenbar geplant','Credits planned')}</div><div class="metric">${formatNum(info.ects)}</div><div class="small muted">/ 120 ECTS</div></div>
      <div class="card"><div class="label">${tr('Abgeschlossen','Completed')}</div><div class="metric">${formatNum(info.done)}</div><div class="small muted">ECTS</div></div>
      <div class="card"><div class="label">${tr('Aktuell ausgewählte Module','Selected courses')}</div><div class="metric">${selectedCourseCount(p)}</div><div class="small muted">${state.interests.length} ${tr('auf Merkliste','on shortlist')}</div></div>
      <div class="card"><div class="label">${tr('Offene Studienbedingungen','Open requirements')}</div><div class="metric">${info.open}</div><div class="small muted">${tr('Prüfung ist vorläufig','Preliminary audit')}</div></div></div>
    <div class="card spaced"><div class="row between"><h2 class="section-title">${tr('Required Study Achievements – tatsächlicher Stand','Required study achievements – actual progress')}</h2>${button(tr('Details','Details'),'go-requirements')}</div>
      <p class="hint">${tr('Abgeschlossen und erst geplant werden getrennt bewertet. Auflagen sind nicht Teil der 120 ECTS.','Completed and merely planned results are separate. Admission requirements do not count towards the 120 credits.')}</p>${briefRequirements(p)}${allocationIssues(p)}
      <div class="line"></div><div class="row between wrap"><span class="small">${tr('Persönliche Auflagen','Personal admission requirements')}: ${admission.done}/${admission.courses.length} ${tr('bestanden','completed')}</span>${button(tr('RW-Bachelor-Kurse finden','Find RW Bachelor courses'),'browse-rw')}</div>
    </div>
    <div class="card spaced"><div class="row between"><h2 class="section-title">${tr('Deine tatsächlichen Semester','Your actual semesters')}</h2>${button(tr('Bearbeiten','Edit'),'go-semesters')}</div>
      <div class="semester-cols">${p.semesters.map(s=>`<div class="semester-col"><strong>${escape(semName(s))}</strong>${p.lockedSemesters.includes(s)?' 🔒':''}<div class="tiny muted" style="margin-top:9px">${p.courses.filter(c=>c.semester===s).length} ${tr('Module','courses')}</div></div>`).join('')}</div></div>
    <div class="card spaced"><div class="row between"><h2 class="section-title">${tr('Hypothetische Szenarien','Hypothetical scenarios')}</h2>${button(tr('Vergleichen','Compare'),'go-plans')}</div>
      <p class="muted small">${tr('Spezialisierungen beeinflussen den tatsächlichen Studienverlauf nicht, solange du sie nicht bewusst übernimmst.','Specialisations do not change your actual study record until you explicitly adopt them.')}</p>
      <div class="scenario-tiles">${state.plans.map(s=>`<div class="scenario-tile"><strong>${escape(s.name)}</strong><span class="small muted">${escape(s.specialisation||'–')} · ${formatNum(planSummary(s).ects)} ECTS</span><button class="smallbtn" data-action="edit-scenario" data-id="${attrs(s.id)}">${tr('Szenario bearbeiten','Edit scenario')}</button></div>`).join('')}</div></div>`;
}

// Comparison controls are UI-only; no extra personal data is written to disk.
function comparisonSelection() {
  const validPlan = value => allPlans().find(p => p.id === value);
  const a = validPlan(comparison.leftPlan) || plan();
  const b = validPlan(comparison.rightPlan) || state.plans.find(p => p.id !== a.id) || a;
  const semester = (p, chosen, alternative) => p.semesters.includes(chosen) ? chosen :
    p.semesters.includes(alternative) ? alternative : (p.semesters[0] || null);
  const aSem = semester(a, comparison.leftSemester, comparison.rightSemester);
  const bSem = semester(b, comparison.rightSemester, aSem);
  comparison = {leftPlan:a.id,leftSemester:aSem,rightPlan:b.id,rightSemester:bSem};
  return {a,b,aSem,bSem};
}
function comparisonKey(c) {
  const number = String(c.number || '').trim().toUpperCase();
  if (number) return `number:${number}`;
  const title = String(c.title || '').trim().replace(/\s+/g,' ').toLocaleLowerCase();
  return title ? `title:${title}` : `id:${c.id}`;
}
function comparisonChanged(a, b) {
  return MasterPlanRules.allocationRole(a)!==MasterPlanRules.allocationRole(b) || safe(a.ects)!==safe(b.ects) || a.status!==b.status || !!a.locked!==!!b.locked || !!a.proxy!==!!b.proxy;
}
function compareSemesterCourses(a, b) {
  // Do not lose repeated catalogue entries: pair each occurrence at most once.
  const remaining = new Map();
  b.forEach(c => {const key=comparisonKey(c);if(!remaining.has(key))remaining.set(key,[]);remaining.get(key).push(c);});
  const same=[], left=[];
  a.forEach(c => {const choices=remaining.get(comparisonKey(c));if(choices?.length)same.push([c,choices.shift()]);else left.push([c,null]);});
  const right=[...remaining.values()].flat().map(c=>[null,c]);
  return {same,left,right,rows:[...same,...left,...right]};
}
function semesterCompareCard(c) {
  if(!c)return `<div class="compare-placeholder" aria-label="${tr('Nicht vorhanden','Not present')}">—</div>`;
  const ects=credited(c)?safe(c.ects):0;
  return `<div class="semester-course compare-course ${c.role==='extra'?'extra':''} ${c.proxy?'proxy':''}">
    <div class="row between"><strong>${escape(c.title||c.number||tr('Unbenanntes Modul','Untitled course'))}</strong>${c.locked?`<span title="${tr('Modul fixiert','Course locked')}">🔒</span>`:''}</div>
    <div class="small muted">${escape(c.number||tr('Manuelles Modul','Manual course'))} · ${escape(trRole(MasterPlanRules.allocationRole(c)))} · ${escape(c.status||'planned')}</div>
    <div class="badge-group" style="margin-top:9px">${pill(`${formatNum(ects)} ${tr('angerechnete ECTS','credited ECTS')}`,c.role==='extra'?'orange':'')}${c.proxy?pill(`${tr('Proxy','Proxy')}: ${semName(c.sourceSemester)}`,'orange'):''}</div>
  </div>`;
}
function semesterComparison() {
  const {a,b,aSem,bSem}=comparisonSelection();
  const options=(p,selected)=>p.semesters.map(s=>`<option value="${attrs(s)}" ${s===selected?'selected':''}>${escape(semName(s))}</option>`).join('');
  const planOptions=(chosen)=>allPlans().map(p=>`<option value="${attrs(p.id)}" ${p.id===chosen?'selected':''}>${escape(p.name)}</option>`).join('');
  const left=allCourses(a).filter(c=>c.semester===aSem),right=allCourses(b).filter(c=>c.semester===bSem);
  const compared=compareSemesterCourses(left,right);
  const total = cs => cs.filter(credited).reduce((sum,c)=>sum+safe(c.ects),0);
  const summarize=(p,s,cs)=>`<div class="compare-head"><div><h3>${escape(p.name)} <span class="muted">· ${escape(semName(s))}</span></h3><div class="small muted">${cs.length} ${tr('Module','courses')} · ${formatNum(total(cs))} ${tr('anrechenbare ECTS (vorläufig)','credited ECTS (provisional)')}</div></div>${p.lockedSemesters.includes(s)?pill(tr('Semester fixiert','Semester locked'),'gray'):''}</div>`;
  return `<div class="compare-controls">
     <div class="compare-control"><label for="compare-left-plan">${tr('Plan A','Plan A')}</label><select id="compare-left-plan">${planOptions(a.id)}</select><label for="compare-left-sem">${tr('Semester A','Semester A')}</label><select id="compare-left-sem">${options(a,aSem)}</select></div>
     <div class="compare-switch" aria-hidden="true">⇄</div>
     <div class="compare-control"><label for="compare-right-plan">${tr('Plan B','Plan B')}</label><select id="compare-right-plan">${planOptions(b.id)}</select><label for="compare-right-sem">${tr('Semester B','Semester B')}</label><select id="compare-right-sem">${options(b,bSem)}</select></div>
   </div>
   <div class="compare-summary"><span>${pill(`${compared.same.length} ${tr('gemeinsam','in common')}`,'green')}</span><span>${pill(`${compared.left.length} ${tr('nur links','left only')}`)}</span><span>${pill(`${compared.right.length} ${tr('nur rechts','right only')}`)}</span><span>${pill(`${compared.same.filter(([x,y])=>comparisonChanged(x,y)).length} ${tr('geänderte Details','changed details')}`,'orange')}</span></div>
   <div class="semester-diff">
     <div>${summarize(a,aSem,left)}</div><div>${summarize(b,bSem,right)}</div>
     ${compared.rows.length ? compared.rows.map(([ac,bc])=>`<div class="compare-pair ${ac&&bc?'compare-common':'compare-unique'}">
       <div class="compare-pair-label">${ac&&bc?tr('In beiden Semestern','In both semesters'):ac?tr('Nur in Semester A','Semester A only'):tr('Nur in Semester B','Semester B only')}${ac&&bc&&comparisonChanged(ac,bc)?` · ${tr('Unterschiedliche Details','Different details')}`:''}</div>
       <div class="compare-pair-grid">${semesterCompareCard(ac)}${semesterCompareCard(bc)}</div>
     </div>`).join(''):`<p class="no-results compare-empty">${tr('Beide Semester enthalten noch keine Module.','Both semesters have no courses yet.')}</p>`}
   </div>
   <p class="hint">${tr('Vergleich inklusive fixierter und freiwilliger Kurse. Zusatzkurse zählen mit 0 anrechenbaren ECTS; die Anrechnung bleibt vorläufig.','Comparison includes locked and extra courses. Extra courses count as 0 credited ECTS; credit eligibility remains provisional.')}</p>`;
}
function plans() {
  const options=allPlans();
  return `${pageHeader(tr('Szenarien vergleichen','Compare scenarios'),tr('Szenarien sind hypothetisch. Dein tatsächlicher Studienverlauf bleibt separat.','Scenarios are hypothetical. Your actual record remains separate.'),button('+ '+tr('Neues Szenario','New scenario'),'new-plan','','button'))}
    <div class="row between card" style="margin-bottom:18px"><div><strong>${tr('Tatsächliches Studium','Actual studies')}</strong><p class="small muted">${tr('Unabhängig von den Szenarien','Independent of scenarios')}</p></div>${button(tr('Realen Verlauf öffnen','Open actual plan'),'edit-actual')}</div>
    <div class="grid columns-2">${state.plans.map(x=>{const s=planSummary(x);return `<div class="card"><div class="label">${tr('Szenario / Was wäre wenn?','Scenario / what if?')}</div><h2 style="font-size:19px;margin:10px 0">${escape(x.name)}</h2>
      <p class="small muted">${escape(x.specialisation||'–')}</p><div class="actions">${pill(`${formatNum(s.ects)} ECTS`)}${pill(`${s.open} ${tr('offen','open')}`)}</div>
      <div class="actions" style="margin-top:14px">${button(tr('Öffnen','Open'),'edit-scenario',`data-id="${attrs(x.id)}"`,'button')}${button(tr('Duplizieren','Duplicate'),'duplicate-plan',`data-id="${attrs(x.id)}"`)}${button(tr('Umbenennen','Rename'),'rename-plan',`data-id="${attrs(x.id)}"`)}${button(tr('Löschen','Delete'),'delete-plan',`data-id="${attrs(x.id)}"`,'dangerbtn')}</div></div>`;}).join('')}</div>
    <div class="card spaced"><h2 class="section-title">${tr('Vergleich','Comparison')}</h2>
      <div class="tabs"><button class="tab ${comparisonView==='plans'?'active':''}" data-action="compare-view" data-view="plans">${tr('Alle Anforderungen','All requirements')}</button><button class="tab ${comparisonView==='semesters'?'active':''}" data-action="compare-view" data-view="semesters">${tr('Semester vs. Semester','Semester vs. semester')}</button></div>
      ${comparisonView==='semesters'?semesterComparison():`<div class="table-wrap"><table><thead><tr><th>${tr('Merkmal','Measure')}</th>${options.map(x=>`<th>${escape(x.name)}</th>`).join('')}</tr></thead><tbody>
        ${[[tr('ECTS geplant','Planned ECTS'),x=>formatNum(planSummary(x).ects)],[tr('Offene Bedingungen','Open rules'),x=>planSummary(x).open],[tr('Zusatzkurse','Extra courses'),x=>planSummary(x).extras],[tr('Module','Courses'),x=>x.courses.length]].map(([label,fn])=>`<tr><td>${escape(label)}</td>${options.map(x=>`<td>${escape(fn(x))}</td>`).join('')}</tr>`).join('')}
      </tbody></table></div><div class="line"></div>${options.map(x=>`<details class="scenario-requirements"><summary><strong>${escape(x.name)}</strong> · ${tr('Required Study Achievements','Required study achievements')}</summary>${briefRequirements(x)}</details>`).join('')}`}</div>`;
}

let allocationEdit=null;
function allocationEditor(){
  if(!allocationEdit)return '';
  const source=getPlan(allocationEdit.planId),c=source.courses.find(c=>c.id===allocationEdit.courseId);
  if(!c)return '';
  return `<div class="card spaced" id="allocation-editor"><h2>${tr('Zuordnung ändern','Change allocation')}: ${escape(c.title)}</h2><form id="reassign-form">
    <label>${tr('Zielplan','Target plan')}<select name="plan">${allPlans().map(p=>`<option value="${attrs(p.id)}" ${p.id===source.id?'selected':''}>${escape(p.name)}</option>`).join('')}</select></label>
    <label>${tr('Semester','Semester')}<select name="semester">${[...new Set(allPlans().flatMap(p=>p.semesters).concat(recentTerms()))].sort().map(t=>`<option ${t===c.semester?'selected':''} value="${t}">${semName(t)}</option>`).join('')}</select></label>
    <label>${tr('Anrechnungskategorie','Credit category')}<select name="role">${roleList.map(r=>`<option ${r===MasterPlanRules.allocationRole(c)?'selected':''} value="${r}">${escape(trRole(r))}</option>`).join('')}</select></label>
    <p class="hint">${tr('Bei Semesterwechsel werden gewählte Termine zurückgesetzt. Historische Referenzen sind erlaubt und werden als unbestätigt markiert.','Changing semester resets selected events. Historical references are allowed and labelled as unconfirmed.')}</p>
    ${button(tr('Übernehmen','Apply'),'apply-reassignment','','button')}${button(tr('Abbrechen','Cancel'),'cancel-reassignment')}</form></div>`;
}
function offeringWarnings(c){
  if(!c.sourceSemester||!c.semester||c.sourceSemester===c.semester)return '';
  return `<span data-warning="historical">${pill(tr('Historische Referenz – kein bestätigtes Angebot: ','Historical reference – no confirmed offering: ')+semName(c.sourceSemester),'orange')}</span>${c.sourceSemester.slice(-1)!==c.semester.slice(-1)?`<span data-warning="season">${pill(tr('Achtung: FS/HS weicht vom Zielsemester ab','Warning: spring/autumn differs from target semester'),'orange')}</span>`:''}`;
}
function semesterBoard(p) {
  return `<div class="semester-cols">${p.semesters.map(sem=>{
    const locked=p.lockedSemesters.includes(sem),rows=allCourses(p).filter(c=>c.semester===sem);
    return `<section class="semester-col" data-drop-plan="${attrs(p.id)}" data-drop-sem="${attrs(sem)}"><div class="row between"><div><strong>${escape(semName(sem))}</strong><div class="tiny muted">${formatNum(rows.filter(credited).reduce((v,c)=>v+safe(c.ects),0))} ECTS</div></div>
      <button class="smallbtn" data-action="lock-semester" data-plan-id="${attrs(p.id)}" data-sem="${attrs(sem)}" title="${tr('Semester fixieren','Lock semester')}">${locked?'🔒':'🔓'}</button>${button('×','remove-semester',`data-plan-id="${attrs(p.id)}" data-sem="${attrs(sem)}" title="${tr('Semester entfernen','Remove semester')}"`)}</div>
      ${rows.length?rows.map(c=>`<div draggable="${!fixed(c,p)&&p.courses.some(x=>x.id===c.id)}" data-drag-plan="${attrs(p.id)}" data-drag-course="${attrs(c.id)}" class="semester-course ${c.role==='extra'?'extra':''} ${c.proxy?'proxy':''}"><div class="row between"><strong>${moduleTitle(c)}</strong>${c.locked?'🔒':''}</div>
        <div class="small muted">${escape(c.number||'')} · ${escape(trRole(MasterPlanRules.allocationRole(c)))}</div>${courseLinks(c)}
        <div class="badge-group" style="margin-top:8px">${pill(`${formatNum(credited(c)?c.ects:0)} ${tr('anrechenbar','credited')}`,c.role==='extra'||c.role==='requirement'?'orange':'')}${offeringWarnings(c)}</div>
        <div class="actions" style="margin-top:12px">${button(tr('Zuordnung ändern','Change allocation'),'reassign-course',`data-id="${attrs(c.id)}" data-plan-id="${attrs(p.id)}"`)}${button(tr('Bearbeiten','Edit'),'edit-course',`data-id="${attrs(c.id)}" data-plan-id="${attrs(p.id)}"`)}${button(c.locked?'🔒':'🔓','lock-course',`data-id="${attrs(c.id)}" data-plan-id="${attrs(p.id)}"`)}
          ${button(tr('Abwählen','Remove'),'remove-course',`data-id="${attrs(c.id)}" data-plan-id="${attrs(p.id)}"`, 'dangerbtn')}</div></div>`).join(''):`<p class="no-results">${tr('Noch keine Module zugewiesen','No assigned courses yet')}</p>`}
      <div class="actions" style="margin-top:14px">${button('+ '+tr('Kurs aus Merkliste','Course from shortlist'),'focus-assign',`data-plan-id="${attrs(p.id)}" data-sem="${attrs(sem)}"`)}</div></section>`;
  }).join('')}</div>`;
}
let selectedInterests=new Set(), assignmentContext=null;
function refreshAssignmentChoices(){
  const form=$('#assign-course-form');if(!form)return;
  const planId=formVal(form,'plan'),term=formVal(form,'semester'),query=formVal(form,'filter').toLowerCase();
  assignmentContext={page,planId,term,role:formVal(form,'role'),query};
  const available=MasterPlanRules.availableShortlist(state,planId);
  const allowed=new Set(available.map(i=>i.id));selectedInterests=new Set([...selectedInterests].filter(i=>allowed.has(i)));
  $('#assignment-choices').innerHTML=available.filter(i=>`${i.title} ${i.number||''}`.toLowerCase().includes(query)).map(i=>{
    return `<label class="assignment-choice"><input type="checkbox" name="interest" value="${attrs(i.id)}" ${selectedInterests.has(i.id)?'checked':''}><span><strong>${escape(i.title)}</strong><br><small>${escape(i.number||'')} · ${formatNum(i.ects)} ECTS · ${escape(trRole(i.suggestedRole||'elective'))}${(i.unitId||Object.keys(i.offerings||{}).length)&&!i.offerings?.[term]&&i.sourceSemester!==term?' · '+tr('Historische Referenz – Angebot unbestätigt','Historical reference – offering unconfirmed'):''}</small></span></label>`;
  }).join('')||`<p class="muted">${tr('Keine unzugewiesenen Module gefunden.','No unassigned modules found.')}</p>`;
  $('#assignment-count').textContent=`${selectedInterests.size} ${tr('ausgewählt','selected')}`;
}
function assignmentForm(p=plan()) {const ctx=assignmentContext?.page===page?assignmentContext:{planId:p.id,term:page==='schedule'?schedule.current:p.semesters[0],role:'suggested',query:''};return `<form id="assign-course-form"><div class="filterbar align-end">
      <div class="field"><label>${tr('Zielplan','Target plan')}</label><select name="plan">${allPlans().map(x=>`<option value="${attrs(x.id)}" ${x.id===ctx.planId?'selected':''}>${escape(x.name)}</option>`).join('')}</select></div>
      <div class="field"><label>${tr('Zielsemester','Target semester')}</label><select name="semester">${Array.from(new Set(allPlans().flatMap(x=>x.semesters).concat(recentTerms()))).sort().map(x=>`<option value="${attrs(x)}" ${x===ctx.term?'selected':''}>${semName(x)}</option>`).join('')}</select></div>
      <div class="field"><label>${tr('Anrechnungskategorie','Credit category')}</label><select name="role"><option value="suggested" ${ctx.role==='suggested'?'selected':''}>${tr('Jeweilige Kategorie beibehalten','Keep each suggested category')}</option>${roleList.map(x=>`<option value="${x}" ${ctx.role===x?'selected':''}>${escape(trRole(x))}</option>`).join('')}</select></div></div>
      <p class="hint">${tr('Bereits im Zielplan zugewiesene oder abgeschlossene Module sind ausgeblendet. Bestehende Kurse per Drag-and-drop oder „Zuordnung ändern“ verschieben.','Modules already assigned or completed in the target plan are hidden. Move existing courses by drag-and-drop or Change allocation.')}</p>
      <label>${tr('Merkliste filtern','Filter shortlist')}<input name="filter" type="search" value="${attrs(ctx.query)}" placeholder="${tr('Titel oder Kursnummer','Title or course number')}"></label>
      <div class="actions">${button(tr('Sichtbare auswählen','Select visible'),'select-visible')}${button(tr('Auswahl löschen','Clear selection'),'clear-selection')}<span id="assignment-count" role="status"></span></div>
      <div id="assignment-choices" class="assignment-choices"></div><div class="actions">${button(tr('Ausgewählte zuweisen','Assign selected'),'assign-interest','','button')}${button(tr('Modulkatalog','Catalogue'),'go-catalog')}${button(tr('Eigenen Kurs erfassen','Add a custom course'),'manual-course')}</div></form>`;}

function semesters() {
  const p=plan(),interests=state.interests||[];
  return `${pageHeader(tr('Semesterplanung','Semester planning'),tr('Zuerst den echten Studienverlauf pflegen; darunter sind unabhängige Spezialisierungsszenarien.','Maintain your actual record first; below are independent specialisation scenarios.'),button(tr('Semester vergleichen','Compare semesters'),'go-semester-compare'))}
    <div class="card" style="margin-bottom:19px"><div class="row between wrap"><div><h2 class="section-title">${tr('Tatsächliches Studium','Actual studies')}</h2><p class="small muted">${tr('Hier nur deine realen Entscheidungen. Keine Szenario-Spezialisierung.','Only your actual choices. No scenario specialisation.')}</p></div>
    <div class="actions">${button('+ '+tr('Semester hinzufügen','Add semester'),'add-semester','data-plan-id="actual"')}</div></div>${semesterBoard(actual())}</div>
    <div class="card"><div class="row between wrap"><div><h2 class="section-title">${tr('Aus Merkliste einem Semester zuweisen','Assign shortlisted course to a semester')}</h2><p class="small muted">${tr('Katalog → zuerst interessante Module merken; hier daraus auswählen.','Catalogue → shortlist interesting courses first; select them here.')}</p></div>${button(tr('Modulkatalog öffnen','Open catalogue'),'go-catalog')}</div>
    ${assignmentForm(p)}${allocationEditor()}
      <p class="hint">${tr('Für ein Seminar die Kategorie «Spezialisierungsseminar» wählen. Seine ECTS zählen zur Spezialisierung; es ersetzt keine der vier Vorlesungen.','Choose Specialisation seminar for a seminar. Its credits count towards the specialisation; it does not replace any of the four lectures.')}</p></div>
    <div class="card spaced"><div class="row between wrap"><div><h2 class="section-title">${tr('Szenarien / alternative Spezialisierungen','Scenarios / alternative specialisations')}</h2><p class="small muted">${tr('Diese Semester sind hypothetisch und ändern deinen tatsächlichen Verlauf nicht.','These semesters are hypothetical and do not change the actual study record.')}</p></div>${button('+ '+tr('Neues Szenario','New scenario'),'new-plan')}</div>
      <div class="scenario-tiles">${state.plans.map(x=>`<div class="scenario-tile ${state.activePlan===x.id?'selected':''}"><strong>${escape(x.name)}</strong><div class="small muted">${escape(x.specialisation||'–')}</div>${button(tr('Bearbeiten','Edit'),'edit-scenario',`data-id="${attrs(x.id)}"`)}</div>`).join('')}</div>
      ${p.id!=='actual'?`<div class="line"></div><div class="row between wrap"><div><h3>${escape(p.name)}</h3><p class="small muted">${tr('Separates Planszenario','Separate planning scenario')} · ${escape(p.specialisation||'')}</p></div>${button('+ '+tr('Semester','Semester'),'add-semester',`data-plan-id="${attrs(p.id)}"`)}</div>
       <div class="field" style="max-width:310px;margin-bottom:14px"><label>${tr('Spezialisierung des Szenarios','Scenario specialisation')}</label><select id="scenario-specialisation"><option value="">${tr('Noch keine','None yet')}</option>${specialisations.map(x=>`<option ${p.specialisation===x?'selected':''}>${escape(x)}</option>`).join('')}</select></div>
       ${semesterBoard(p)}<div class="line"></div><h3>${tr('Anforderungen für dieses Szenario','Requirements for this scenario')}</h3>${briefRequirements(p)}`:
      `<p class="small muted" style="margin-top:16px">${tr('Wähle oben ein Szenario, um dessen Semester unabhängig zu bearbeiten.','Choose a scenario above to edit its semesters independently.')}</p>`}
    </div>`;
}

function schedule() {
  const p=plan();let semester=p.semesters.includes(schedule.current)?schedule.current:p.semesters[0];schedule.current=semester;
  const days=state.language==='de'?['Mo','Di','Mi','Do','Fr','Sa','So']:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const courses=allCourses(p).filter(c=>c.semester===semester);
  const events=courses.flatMap(c=>(c.events||[]).map(e=>({...e,c}))).filter(x=>x.day>=0&&x.day<=6&&x.start&&x.end);
  const timeToM=x=>{const [h,m]=String(x).split(':').map(Number);return h*60+m;};
  const conflicts=new Set();for(let i=0;i<events.length;i++)for(let j=i+1;j<events.length;j++){
    const a=events[i],b=events[j];if(a.day===b.day&&timeToM(a.start)<timeToM(b.end)&&timeToM(b.start)<timeToM(a.end)){conflicts.add(a.c.id+'-'+a.day);conflicts.add(b.c.id+'-'+b.day);}
  }
  const cells=[];for(let h=8;h<=19;h++){cells.push(`<div class="hour">${String(h).padStart(2,'0')}:00</div>`);
    for(let d=0;d<7;d++){const matching=events.filter(e=>e.day===d&&timeToM(e.start)<(h+1)*60&&timeToM(e.end)>h*60&&timeToM(e.start)>=h*60);
      cells.push(`<div class="daycell" role="button" tabindex="0" data-action="place-slot" data-day="${d}" data-start="${String(h).padStart(2,'0')}:00">${matching.map(e=>`<div class="event ${e.c.role==='extra'?'extra':''} ${conflicts.has(e.c.id+'-'+e.day)?'conflict':''}" title="${attrs(e.c.title)}"><strong>${escape(e.c.title)}</strong><div class="tiny">${escape(e.start)}–${escape(e.end)}</div><div class="tiny">${escape(e.building||'')} ${escape(e.floor||'')} ${escape(e.room||'')}</div></div>`).join('')}</div>`);}}
  return `${pageHeader(tr('Stundenplan','Timetable'),tr('Wähle erst den Kurs aus deinem belegten Semester; kein manuelles Suchen nötig.','Choose a course already assigned to this semester; no manual search needed.'))}
    <div class="row wrap" style="margin-bottom:16px"><label class="inline-label">${tr('Studienplan','Study plan')} ${programmeOptions()}</label>
      <select id="schedule-sem" class="plan-select">${p.semesters.map(x=>`<option value="${x}" ${x===semester?'selected':''}>${semName(x)}</option>`).join('')}</select>
      ${button('+ '+tr('Module zuweisen','Assign courses'),'focus-schedule-assign')}</div>
    ${conflicts.size?`<div class="note">⚠ ${tr('Zeitüberschneidungen','Overlapping events')}: ${conflicts.size}</div>`:''}
    <div class="card" id="schedule-modules"><h2>${tr('Module dieses Semesters','Modules in this semester')}</h2><p>${tr('Modul in eine Zeitzelle ziehen oder eine Zeitzelle anklicken. Danach Zeit prüfen und speichern. Ein Modul kann mehrere Termine haben.','Drag a module onto a time cell or click a time cell. Review and save the time. A module may have multiple meetings.')}</p>${courses.filter(c=>p.courses.some(x=>x.id===c.id)).map(c=>`<button type="button" class="schedule-module" data-action="choose-schedule-module" data-id="${attrs(c.id)}" draggable="${!fixed(c,p)}" data-schedule-course="${attrs(c.id)}">${escape(c.title)} ${fixed(c,p)?'🔒':''}</button>`).join('')}</div>
    <div class="card schedule-wrap"><div class="schedule"><div></div>${days.map(d=>`<div class="dayhead">${d}</div>`).join('')}${cells.join('')}</div></div>
    <div class="card spaced" id="schedule-assignment"><h2>${tr('Modul diesem Semester zuweisen','Assign a course to this semester')}</h2>${assignmentForm(p)}${allocationEditor()}${button(tr('Modul manuell erfassen','Add custom course'),'manual-course',`data-sem="${attrs(semester)}"`)}</div>
    <div class="card spaced"><h2 class="section-title">${tr('Termin hinzufügen','Add a meeting')}</h2>
      ${courses.length?`<form id="event-form"><div id="manual-vvz-link">${courseLinks(courses.find(c=>p.courses.some(x=>x.id===c.id))||courses[0])}</div><div class="filterbar"><div class="field"><label>${tr('Kurs dieses Semesters','Course assigned this term')}</label><select name="course" required>${courses.filter(c=>p.courses.some(x=>x.id===c.id)).map(c=>`<option value="${attrs(c.id)}">${escape(c.title)}</option>`).join('')}</select></div>
        <div class="field"><label>${tr('Wochentag','Weekday')}</label><select name="day">${days.map((d,i)=>`<option value="${i}">${d}</option>`).join('')}</select></div>
        <div class="field"><label>${tr('Beginn','Start')}</label><input name="start" type="time" value="10:00" required></div>
        <div class="field"><label>${tr('Ende','End')}</label><input name="end" type="time" value="12:00" required></div></div>
        <div class="field-row three"><div class="field"><label>${tr('Gebäude','Building')}</label><input name="building" placeholder="HG"></div><div class="field"><label>${tr('Stockwerk','Floor')}</label><input name="floor" placeholder="F"></div><div class="field"><label>${tr('Raum','Room')}</label><input name="room" placeholder="F 1"></div></div>
        <div class="actions" style="margin-top:14px"><button class="button" type="submit">${tr('Termin speichern','Save event')}</button></div></form>`:
        `<p class="note">${tr('Du hast diesem Semester noch keine Kurse zugewiesen. Wähle zuerst Kurse aus deiner Merkliste.','No courses have been assigned this term. Choose them from your shortlist first.')}</p>${button(tr('Zur Semesterplanung','Go to semester planning'),'go-semesters')}`}
    </div><div class="card spaced"><h2 class="section-title">${tr('Kurse und Termine im ausgewählten Semester','Courses and events this semester')}</h2>
    <p class="hint">${tr('VVZ-Termine werden automatisch im Hintergrund geladen (höchstens eine VVZAPI-Anfrage pro Minute; nur bei Bedarf online). Wähle die gewünschten Slots, z. B. deine Übungsgruppe, aus. Bereits manuelle Termine werden nicht überschrieben.','VVZ meetings are loaded automatically in the background (at most one VVZAPI request per minute; online only if needed). Choose the relevant slots such as your exercise group. Manual events are never overwritten.')}</p>
    ${courses.map(c=>{const info=c.unitId?meetingData.get(String(c.unitId)):null;const slots=info?.meetings||[];return `<div class="meeting-unit"><div class="course-card"><div><div class="course-name">${moduleTitle(c)}</div><div class="course-meta">${escape(c.number||'')} · ${trRole(MasterPlanRules.allocationRole(c))} ${offeringWarnings(c)}</div>${courseLinks(c)}</div>${p.courses.some(x=>x.id===c.id)?button(tr('Manuelle Termine bearbeiten','Edit meetings'),'edit-events',`data-id="${attrs(c.id)}"`):''}</div>
      ${c.unitId?(info?.status==='ready'?slots.length?`<div class="meeting-options"><div class="small muted">${tr('Offizielle VVZ-Zeitfenster – frei auswählen','Official VVZ time slots – select as needed')}${c.proxy?` · ${tr('Historischer Proxy','Historical proxy')}: ${semName(c.sourceSemester)}`:''}${info.changed?` · ⚠ ${tr('VVZ-Termine geändert','VVZ schedule changed')}`:''}${info.groupStatus==='queued'?` · ${tr('Weitere VVZ-Termine werden nachgeladen','Additional VVZ meetings loading')}`:''}</div>${slots.map((m,i)=>`<label class="meeting-option"><input type="checkbox" data-slot="${attrs(c.id)}" value="${i}" ${c.events?.some(e=>e.apiSlot===m.slotKey)?'checked':''}> <span>${escape(m.label||'')} · ${escape(['Mo','Di','Mi','Do','Fr','Sa','So'][m.day]||'')} ${escape(m.start||'')}–${escape(m.end||'')} · ${escape([m.building,m.floor,m.room].filter(Boolean).join(' '))}${m.date?` · ${escape(m.date)}`:''}${m.note?`<br><small class="muted">${escape(m.note)}</small>`:''}</span></label>`).join('')}${button(tr('Auswahl übernehmen','Apply selected slots'),'apply-vvz-slots',`data-id="${attrs(c.id)}"`)}</div>`:`<p class="small muted">${info.groupStatus==='queued'?tr('Fehlende Zeiten werden von ETH VVZ nachgeladen; bitte kurz warten.','Missing times are loading from ETH VVZ; please wait.'):info.groupStatus==='failed'?escape(info.error||tr('ETH VVZ momentan nicht erreichbar; erneuter Versuch folgt.','ETH VVZ currently unavailable; will retry.')):tr('Keine regulären Zeiten gefunden; manuelle Eingabe möglich.','No regular times found; manual entry available.')}</p>`:`<p class="small muted">${info?.status==='failed'?escape(info.error):tr('VVZ-Termine werden geladen / warten auf API-Limit…','Loading VVZ meetings / waiting for API rate limit…')}</p>`):`<p class="small muted">${tr('Manueller Kurs – keine VVZ-Kennung vorhanden.','Manual course – no VVZ unit ID.')}</p>`}</div>`;}).join('')||`<p class="muted small">${tr('Keine Kurse','No courses')}</p>`}</div>`;
}

function catalog() {
  const interest=MasterPlanRules.availableShortlist(state,state.activePlan);
  const categories=[['',tr('Alle Kategorien','All categories')],['core','Core Courses'],['elective','Electives'],['specialisation',tr('Spezialisierung','Specialisation')],
    ['case','Case Studies'],['project',tr('Semesterarbeit','Semester project')],['sip','Science in Perspective'],['thesis',tr('Masterarbeit','Master thesis')],
    ['scientific','Scientific Works (0 ECTS)'],['requirement',tr('Zulassungsauflagen (RW Bachelor)','Admission requirements (RW Bachelor)')],['eligible-core',tr('MSc-Corekurse → CSE-Electives','MSc core courses → CSE electives')]];
  const terms=recentTerms();const semesterChoices=[...Array.from(new Set([...terms,...allPlans().flatMap(x=>x.semesters)])).sort().map(x=>[x,semName(x)])];
  return `${pageHeader(tr('Modulkatalog & Merkliste','Course catalogue & shortlist'),tr('1. Entdecke und merke interessante Kurse. 2. Weise sie in der Semesterplanung zu.','1. Find and shortlist courses. 2. Assign them in semester planning.'),button(tr('Zur Semesterplanung','Semester planning'),'go-semesters','','button'))}
  <div class="card" style="margin-bottom:20px"><div class="row between wrap"><div><h2 class="section-title">★ ${tr('Meine interessanten Module','My shortlisted courses')}</h2><p class="muted small">${tr('Primäre Quelle für deine Semesterplanung – unabhängig vom aktuellen Studienplan.','Primary source for semester planning, independent of the active plan.')}</p></div>
    ${button('+ '+tr('Modul manuell merken','Shortlist manually'),'manual-interest')}</div>
    ${interest.length?`<div class="shortlist-grid">${interest.map(c=>`<div class="shortlist-item"><strong>${moduleTitle(c)}</strong><div class="small muted">${escape(c.number||tr('Eigenes Modul','Custom course'))} · ${formatNum(c.ects)} ECTS · ${escape(trRole(c.suggestedRole||'elective'))}</div>
    ${courseLinks(c)}<div class="actions">${button(tr('Für Semester verwenden','Assign to semester'),'focus-assign',`data-interest-id="${attrs(c.id)}"`)}${button(tr('Entfernen','Remove'),'remove-interest',`data-id="${attrs(c.id)}"`,'dangerbtn')}</div></div>`).join('')}</div>`:
      `<p class="note">${state.interests.length?tr('Alle gemerkten Module sind im Zielplan bereits zugewiesen.','All shortlisted modules are already assigned in this plan.'):tr('Noch keine interessanten Module gespeichert. Die Suche unten ist dein Entdeckungswerkzeug.','No shortlisted courses. The search below is for discovery.')}</p>`}</div>
  <div class="card" style="margin-bottom:20px"><h2 class="section-title">${tr('ETH-Kurse entdecken','Discover ETH courses')}</h2>
    <form id="search-form"><div class="filterbar"><div class="field"><label>${tr('Suchtext / Kursnummer','Search title / course number')}</label><input name="q" value="${attrs(searchParams.q)}" placeholder="Numerical, Robotics …"></div>
      <div class="field"><label>${tr('Studiengang','Degree programme')}</label><select name="programme">${Object.entries(programmes).map(([key,v])=>`<option value="${key}" ${searchParams.programme===key?'selected':''}>${escape(v)}</option>`).join('')}</select></div>
      <div class="field"><label>${tr('Kategorie','Category')}</label><select name="category">${categories.map(([key,v])=>`<option value="${key}" ${searchParams.category===key?'selected':''}>${escape(v)}</option>`).join('')}</select></div>
      <div class="field"><label>${tr('Zielsemester / Zeitraum','Semester / window')}</label><select name="semester">${semesterChoices.map(([key,v])=>`<option value="${key}" ${searchParams.semester.split(',')[0]===key?'selected':''}>${escape(v)}</option>`).join('')}</select></div><div class="field"><label>${tr('Zusätzliches Semester (optional)','Additional semester (optional)')}</label><select name="semester2"><option value="">—</option>${semesterChoices.map(([key,v])=>`<option value="${key}" ${searchParams.semester.split(',')[1]===key?'selected':''}>${escape(v)}</option>`).join('')}</select></div>
    </div><div class="row between wrap"><p class="hint">${tr('Wähle ein oder zwei Semester. Fehlende Angebote werden durch markierte historische Referenzen ergänzt.','Choose one or two semesters. Missing offerings use labelled historical references.')}</p>
      <div class="actions">${button(tr('RW Bachelor / Auflagen','RW Bachelor / requirements'),'browse-rw')}${button(tr('MSc Core Electives','MSc core electives'),'browse-eligible-core')}<button class="button" type="submit">⌕ ${tr('Suchen','Search')}</button></div></div></form></div>
  <div class="grid columns-2"><div class="card"><div class="row between"><h2 class="section-title">${tr('Gefundene Module','Search results')}</h2>${pill(searchState||tr('Noch nicht geladen','Not loaded'))}</div>
    ${results.length?results.map(c=>{const name=state.language==='en'?(c.title_english||c.title):(c.title||c.title_english),off=c.offering||{};
      const stored=state.interests.some(i=>i.number===c.number&&c.number || (!c.number&&i.title===name));return `<div class="course-card"><div><div class="course-name">${moduleTitle({...c,title:name})}</div><div class="course-meta">${escape(c.number)} · ${formatNum(c.credits)} ECTS</div>
        <div class="badge-group" style="margin-top:8px">${(c.coreProgrammes||[]).map(name=>pill(name)).join('')}${Object.keys(c.semesters||{}).map(term=>pill(semName(term))).join('')}${c.eligibleCoreElective?pill(tr('MSc-Core → potenzielles CSE-Elective','MSc core → potentially eligible CSE elective'),'green'):''}${off.proxy?offeringWarnings({sourceSemester:off.source_semester,semester:off.target_semester}):off.unit_id?pill(semName(off.source_semester),'green'):''}</div>${courseLinks({number:c.number,unitId:off.unit_id,sourceSemester:off.source_semester,reviewAvailable:!!(c.rating!=null&&Number(c.rating)>0)})}</div>
        <div class="stack">${button(stored?'✓ '+tr('Gemerkt','Shortlisted'):'+ '+tr('Merken','Shortlist'),'shortlist-result',`data-number="${attrs(c.number)}" ${stored?'disabled':''}`,'button')}${button(tr('Merken & zuweisen','Shortlist & assign'),'shortlist-assign',`data-number="${attrs(c.number)}"`)}${button(tr('Nur besuchen','Attend only'),'shortlist-extra',`data-number="${attrs(c.number)}"`)}</div></div>`;}).join(''):`<p class="no-results">${escape(searchState||tr('Filter wählen und Suche starten.','Choose filters and search.'))}</p>`}
    ${catalogTotal>40?`<div class="actions">${button('←','catalog-prev',catalogOffset===0?'disabled':'')}<span>${catalogOffset+1}–${catalogOffset+results.length} / ${catalogTotal}</span>${button('→','catalog-next',catalogOffset+40>=catalogTotal?'disabled':'')}</div>`:''}
    </div><div class="card"><h2 class="section-title">${tr('Spezialisierungen im Katalog','Catalogue specialisations')}</h2><p class="small muted">${tr('Ausblenden ändert weder reale Studienregeln noch gespeicherte Szenarien.','Hiding does not affect real degree rules or saved scenarios.')}</p>
      <div class="grid columns-2">${specialisations.map(s=>`<label class="check-row"><input type="checkbox" data-spec="${attrs(s)}" ${state.selectedSpecialisations.includes(s)?'checked':''}>${escape(s)}</label>`).join('')}</div>
      <div class="line"></div><p class="hint">${tr('Zulassungsauflagen stehen in deinem persönlichen Zulassungsbrief. Die Suche im RW Bachelor bietet mögliche Kurse, ersetzt jedoch nicht den Brief.','Your admission letter defines your requirements. RW Bachelor search helps find courses but cannot replace that letter.')}</p>
      <p class="hint">${tr('Quelle: Unabhängige VVZAPI. Anrechnung ist nicht automatisch bestätigt.','Source: independent VVZAPI. Credits are not automatically recognised.')}</p></div></div>`;
}

function requirements() {
  const p=plan(), admission=bscRequirements(p);
  return `${pageHeader(tr('Studienregeln & Auflagen','Study requirements & admission conditions'),tr('Jeder reale Plan und jedes Szenario wird separat geprüft. Keine Doppelzählung von ECTS.','The actual record and each scenario are checked separately. No ECTS double counting.'))}
    <div class="card"><div class="row between wrap"><div><h2 class="section-title">${tr('Ausgewerteter Studienplan','Study plan being checked')}</h2><p class="small muted">${p.id==='actual'?tr('Tatsächlicher Stand','Actual progress'):tr('Hypothetisches Szenario','Hypothetical scenario')}</p></div>${programmeOptions()}</div></div>
    <div class="note spaced">${tr('Vorläufige Prüfung nach den MSc-CSE-Guidelines 2026 (Reglement 2024). Das persönliche Reglement, die Kurszuordnung und ETH-Genehmigungen müssen bestätigt werden.','Provisional check based on 2026 MSc CSE guidelines (2024 regulations). Personal regulations, course classification and ETH approvals must be verified.')}</div>
    <div class="grid columns-3 spaced">${requirementRows(p).map(requirementCard).join('')}</div>${allocationIssues(p)}
    <div class="card spaced"><h2 class="section-title">${tr('Auflagen – ausserhalb der 120 Master-ECTS','Admission requirements – outside the 120 MSc credits')}</h2>
      <p class="small muted">${tr('Kurse gemäss deinem Zulassungsbrief eintragen. Auflagen zählen nie zu den Master-ECTS.','Enter the courses from your admission letter. Their credits never count towards the master degree.')}</p>
      ${admission.courses.map(c=>`<div class="course-card"><div><strong>${moduleTitle(c)}</strong><div class="small muted">${escape(c.number||'')} · ${formatNum(c.ects)} ${tr('Auflagen-ECTS','admission credits')}</div></div>${pill(c.status==='completed'?tr('Erfüllt','Done'):tr('Offen / geplant','Open / planned'),c.status==='completed'?'green':'orange')}</div>`).join('')||`<p class="muted small">${tr('Noch keine Auflagen erfasst.','No requirements entered yet.')}</p>`}
      <div class="row between wrap" style="margin-top:15px"><span class="small">${admission.done}/${admission.courses.length} ${tr('Auflagen bestanden','requirements completed')}</span>${button(tr('RW-Bachelor-Kurse finden','Find RW Bachelor courses'),'browse-rw')}</div>
      <div class="line"></div><label class="check-row"><input type="checkbox" id="bsc-scientific" ${state.scientificWorksBSc?'checked':''}>${tr('Scientific Works in Mathematics/Physics bereits im Bachelor erfolgreich abgeschlossen (0 ECTS im Master).','Scientific Works in Mathematics/Physics completed during BSc (0 ECTS in MSc).')}</label>
    </div>
    ${p.id==='actual'?`<div class="card spaced"><h2 class="section-title">${tr('Anforderungen der Szenarien','Scenario requirements')}</h2>${state.plans.map(x=>`<details class="scenario-requirements"><summary>${escape(x.name)}</summary>${briefRequirements(x)}</details>`).join('')}</div>`:''}`;
}

function grades() {
  return `${pageHeader(page==='simulation'?tr('Studiensimulation','Study simulation'):tr('Private Noten','Private grades'),tr('Noten und Simulationen bleiben im passwortverschlüsselten Notenspeicher.','Grades and simulations remain in the password-encrypted grade vault.'))}<div class="card" style="max-width:820px"><div class="row between"><h2 class="section-title">🔒 ${tr('Geschützter Notenbereich','Protected grade vault')}</h2>${gradesCache?button(tr('Sperren','Lock'),'lock-grades'):''}</div>${gradesCache?(page==='simulation'?simulationPanel():renderGradeEditor()):`<p class="muted small">${tr('Passwort eingeben, um die verschlüsselten Noten zu öffnen oder erstmals anzulegen. Ohne Passwort ist keine Wiederherstellung möglich.','Enter a password to unlock or create the encrypted grades. Recovery is impossible without the password.')}</p><form id="grades-unlock-form"><div class="field"><label>${tr('Passwort','Password')}</label><input name="password" type="password" required minlength="8" autocomplete="off" placeholder="${tr('Mindestens 8 Zeichen','At least 8 characters')}"></div><div style="margin-top:13px"><button class="button" type="submit">${tr('Öffnen / erstellen','Unlock / create')}</button></div></form>`}</div>`;
}
function moduleGrade(entry){return MasterPlanRules.moduleGrade(entry);}
function gradeCategory(entry){return entry.category==='specialisation'&&entry.subtype==='seminar'?'excluded':['core','specialisation','elective','thesis'].includes(entry.category)?entry.category:'excluded';}
function calculateFinalGrade(entries){return MasterPlanRules.calculateFinalGrade(entries,guidelines||{});}

let gradeDraft=null,activeSimulation=null;
const privatePages=['grades','simulation'];
function privateNumber(v){return v===''?null:Number(v);}
function gradeMetric(v){return v==null?'—':Number(v).toFixed(2);}
function gradeCategoryChoice(e){return e.category==='specialisation'&&e.subtype==='seminar'?'specialisation-seminar':e.category;}
function gradeFinalCard(entries,simulated=false){
  const final=calculateFinalGrade(simulated?MasterPlanGrades.projectedEntries(entries):entries);
  return `<div class="card spaced" id="private-final"><h2>${simulated?tr('Simulierte Gesamtnote','Simulated final grade'):tr('Gesamtnote aus echten Ergebnissen','Final grade from actual results')}</h2><strong class="metric">${final.complete?gradeMetric(final.value):'—'}</strong>
    <p>${tr('Core-Kurse','Core courses')}: ${final.counts.core}/2 · ${tr('Spezialisierungsvorlesungen','Specialisation lectures')}: ${final.counts.specialisation}/4 · Electives: ${final.counts.elective}/2+ · ${tr('Masterarbeit','Master thesis')}: ${final.counts.thesis}/1</p>
    <p class="hint">${tr('Gewichte: Core je 2, vier Spezialisierungsvorlesungen je 1, jedes Elective 1, Masterarbeit 4. Seminare sind ausgeschlossen. Fehlende oder nicht bestandene Leistungen ergeben keine vollständige Schlussnote.','Weights: each core 2, each of four specialisation lectures 1, each elective 1, thesis 4. Seminars are excluded. Missing or failed results do not produce a complete final grade.')}</p></div>`;
}
function forecastHtml(entry){
  const f=MasterPlanGrades.forecast(entry,entry.targetGrade??4);
  if(!f.valid)return `<p role="status">${tr('Bitte gültige Noten von 1 bis 6 und positive Gewichtungen eingeben.','Enter valid grades from 1 to 6 and positive weights.')}</p>`;
  return `<p>${tr('Bekanntes Gewicht','Known weight')}: ${formatNum(f.knownWeight)} / ${formatNum(f.weight)} · ${tr('Schnitt bekannter Teilnoten','Average of known components')}: ${gradeMetric(f.knownAverage)}</p>
    <p>${tr('Modulnote (nur echte Ergebnisse)','Module grade (actual results only)')}: <strong>${gradeMetric(f.value)}</strong> · ${tr('Mit Annahmen','With assumptions')}: <strong data-projected-grade>${gradeMetric(f.projected)}</strong></p>
    <p>${tr('Möglicher Bereich für offene Leistungen (Noten 1–6)','Possible range for remaining assessments (grades 1–6)')}: ${gradeMetric(f.min)}–${gradeMetric(f.max)}</p>
    ${f.required!=null?`<p>${tr('Benötigter Schnitt der offenen Leistungen für die Zielnote','Required average on remaining assessments for the target grade')}: <strong data-required-grade>${gradeMetric(f.required)}</strong> ${f.reachable===false?tr('(mit maximal 6 nicht erreichbar)','(not achievable with a maximum of 6)'):f.alreadySecured?tr('(auch mit Note 1 bereits gesichert)','(already secured even with grade 1)'):''}</p>`:''}
    ${Math.abs(f.weight-100)>1e-8?`<p class="note">${tr('Die Gewichtungen werden relativ normalisiert; für Prozentangaben sollten sie zusammen 100 ergeben.','Weights are normalized relatively; percentage weights should total 100.')}</p>`:''}`;
}
function draftEditor(){
  if(!gradeDraft)return '';
  const e=gradeDraft.entry,sim=gradeDraft.kind==='simulation';
  const courseOptions=MasterPlanGrades.scenarioCourses(actual(),state.history||[]);
  return `<div class="card spaced" id="grade-editor"><h2>${sim?tr('Notenannahmen bearbeiten','Edit grade assumptions'):tr('Modulnote und Teilnoten bearbeiten','Edit module grade and components')}</h2>
    <form id="grade-entry-form"><div class="filterbar">
    ${!sim?`<label>${tr('Modul aus tatsächlichem Studium (optional)','Course from actual studies (optional)')}<select data-grade-link><option value="">${tr('Manueller Eintrag','Manual entry')}</option>${courseOptions.map(c=>`<option value="${attrs(c.id)}" ${e.courseId===c.id?'selected':''}>${escape(c.title)}</option>`).join('')}</select></label>`:''}
    <label>${tr('Modultitel','Course title')}<input data-grade-input="name" value="${attrs(e.name||'')}" required ${sim?'readonly':''}></label>
    <label>${tr('Kursnummer (optional)','Course number (optional)')}<input data-grade-input="number" value="${attrs(e.number||'')}" ${sim?'readonly':''}></label>
    <label>${tr('Notenkategorie','Grade category')}<select data-grade-input="category" ${sim?'disabled':''}>${['core','specialisation','specialisation-seminar','elective','thesis','excluded'].map(r=>`<option value="${r}" ${r===gradeCategoryChoice(e)?'selected':''}>${r==='excluded'?tr('Nicht in Schlussnote','Exclude from final grade'):escape(trRole(r))}</option>`).join('')}</select></label></div>
    <label class="check-row"><input type="checkbox" data-grade-input="countsForFinal" ${e.countsForFinal!==false?'checked':''} ${sim?'disabled':''}>${tr('Für Schlussnote auswählen','Select for final grade')}</label>
    ${e.actualMatched?`<p class="note">${tr('Echte Ergebnisse aus dem tatsächlichen Studium werden übernommen. Bekannte Teilnoten und ihre Gewichtungen sind hier geschützt.','Actual results from real studies are inherited. Known grades and their assessment weights are protected here.')}</p>`:''}
    <div class="table-wrap"><table><thead><tr><th>${tr('Teilleistung','Assessment')}</th><th>${tr('Gewicht (%)','Weight (%)')}</th><th>${tr('Echte Note','Actual grade')}</th><th>${tr('Annahme für offene Leistung','Assumption for pending assessment')}</th><th></th></tr></thead><tbody>
    ${e.parts.map((p,i)=>`<tr><td><input aria-label="${tr('Bezeichnung','Name')}" data-grade-part="${i}" data-grade-input="name" value="${attrs(p.id==='exam'&&p.name==='Exam'?tr('Prüfung','Exam'):p.name)}" ${p.structureLocked?'readonly':''}></td><td><input aria-label="${tr('Gewicht','Weight')}" type="number" min="0.001" step="any" data-grade-part="${i}" data-grade-input="weight" value="${attrs(p.weight)}" ${p.structureLocked?'readonly':''}></td>
    <td><input aria-label="${tr('Echte Note','Actual grade')}" type="number" min="1" max="6" step="any" data-grade-part="${i}" data-grade-input="value" value="${attrs(p.value??'')}" ${sim?'readonly':''}></td>
    <td><input aria-label="${tr('Annahme','Assumption')}" type="number" min="1" max="6" step="any" data-grade-part="${i}" data-grade-input="estimate" value="${attrs(p.estimate??'')}" ${p.actualLocked||p.value!=null?'disabled':''}></td><td>${!p.structureLocked?button('×','grade-part-remove',`data-index="${i}" aria-label="${tr('Teilleistung entfernen','Remove assessment')}"`):'🔒'}</td></tr>`).join('')}</tbody></table></div>
    ${!e.actualMatched?button('+ '+tr('Teilleistung','Assessment'),'grade-part-add'):''}
    <div class="filterbar"><label>${tr('Additiver Notenbonus (z. B. +0,25)','Additive grade bonus (e.g. +0.25)')}<input type="number" step="any" min="-6" max="6" data-grade-input="bonus" value="${attrs(e.bonus??0)}" ${e.bonusLocked?'readonly':''}></label>
    <label>${tr('Gewünschte Modulnote','Target module grade')}<input type="number" min="1" max="6" step="any" data-grade-input="targetGrade" value="${attrs(e.targetGrade??4)}"></label></div>
    <p class="hint">${tr('Echte Noten nur für bereits bewertete Leistungen eintragen. Offene Noten leer lassen und separat als Annahme testen. Der Bonus wird nach dem gewichteten Durchschnitt addiert; maximal Note 6.','Enter actual grades only for assessed work. Leave pending grades blank and test them separately as assumptions. The bonus is added after the weighted average; grades are capped at 6.')}</p>
    <div id="grade-preview" aria-live="polite">${forecastHtml(e)}</div><div class="actions"><button class="button" type="submit">${tr('Übernehmen','Apply')}</button>${button(tr('Abbrechen','Cancel'),'grade-draft-cancel')}</div></form></div>`;
}
function renderGradeEditor(){
  const entries=gradesCache.entries;
  return `${gradeFinalCard(entries)}<p class="note">${tr('Annahmen sind keine echten Ergebnisse. Alle Änderungen erst mit „Verschlüsselt speichern“ dauerhaft sichern.','Assumptions are not actual results. Save changes permanently using Save encrypted.')}</p>
    <div class="actions">${button('+ '+tr('Modulnote','Course grade'),'grade-add','','button')}${button(tr('Verschlüsselt speichern','Save encrypted'),'grade-save','','button')}</div>
    ${entries.map((e,i)=>`<div class="card spaced"><h3>${escape(e.name)}</h3><p>${tr('Modulnote','Module grade')}: ${gradeMetric(moduleGrade(e))} · ${tr('Prognose','Projection')}: ${gradeMetric(MasterPlanGrades.forecast(e).projected)}</p>${button(tr('Bearbeiten','Edit'),'grade-edit',`data-index="${i}"`)}${button(tr('Entfernen','Remove'),'grade-delete',`data-index="${i}"`)}</div>`).join('')}${draftEditor()}`;
}
function simulationEntries(s){
  const plan=allPlans().find(p=>p.id===s.planId);if(!plan)return [];
  return MasterPlanGrades.scenarioCourses(plan,state.history||[]).map(c=>MasterPlanGrades.simulationEntry(c,s.entries[MasterPlanGrades.key(c)],gradesCache.entries,s.planId==='actual'));
}
function simulationPanel(){
  const sims=gradesCache.simulations;
  const selected=sims.find(s=>s.id===activeSimulation)||sims[0];activeSimulation=selected?.id||null;
  const entries=selected?simulationEntries(selected):[];
  return `<p class="note">${tr('Simulationen sind hypothetisch und ändern weder echte Noten noch Semesterzuweisungen. Beim tatsächlichen Studienplan werden eindeutig zugeordnete echte Ergebnisse automatisch übernommen.','Simulations are hypothetical and change neither actual grades nor course allocations. Selecting actual studies automatically inherits unambiguously linked real results.')}</p>
    <form id="simulation-create-form" class="card"><label>${tr('Neues Notenszenario','New grade scenario')}<input name="name" required maxlength="150" placeholder="${tr('z. B. Optimistisch','e.g. Optimistic')}"></label><button class="button" type="submit">${tr('Szenario erstellen','Create scenario')}</button></form>
    <div class="actions">${button(tr('Verschlüsselt speichern','Save encrypted'),'grade-save','','button')}</div>
    ${selected?`<div class="card spaced"><label>${tr('Notenszenario','Grade scenario')}<select id="simulation-select">${sims.map(s=>`<option value="${attrs(s.id)}" ${s.id===selected.id?'selected':''}>${escape(s.name)}</option>`).join('')}</select></label>
    <label>${tr('Semesterplanung auswählen','Choose study plan')}<select id="simulation-plan">${!allPlans().some(p=>p.id===selected.planId)?`<option selected value="">${tr('Plan wurde entfernt – bitte auswählen','Plan was removed – choose another')}</option>`:''}${allPlans().map(p=>`<option value="${attrs(p.id)}" ${p.id===selected.planId?'selected':''}>${escape(p.name)}</option>`).join('')}</select></label>${button(tr('Szenario duplizieren','Duplicate scenario'),'simulation-duplicate')}${button(tr('Szenario löschen','Delete scenario'),'simulation-delete')}</div>
    ${gradeFinalCard(entries,true)}
    ${entries.map(e=>`<div class="card spaced"><h3>${escape(e.name)}</h3><p>${escape(trRole(MasterPlanRules.allocationRole({role:e.category,subtype:e.subtype})))}</p>${e.actualMatched?pill(tr('Echte Ergebnisse übernommen','Actual results inherited'),'green'):''}<p>${tr('Simulierte Modulnote','Simulated module grade')}: ${gradeMetric(MasterPlanGrades.forecast(e).projected)}</p>${button(tr('Teilnoten / Annahmen','Components / assumptions'),'simulation-edit',`data-key="${attrs(MasterPlanGrades.key({...e,id:e.courseId}))}"`)}</div>`).join('')||`<p>${tr('Dem gewählten Plan sind noch keine anrechenbaren Module zugewiesen.','The selected plan has no credit-bearing courses assigned yet.')}</p>`}${draftEditor()}`:''}`;
}
async function privateAction(action,element){
  if(action==='grade-add'||action==='grade-edit'){
    const index=action==='grade-edit'?Number(element.dataset.index):-1;
    gradeDraft={kind:'real',index,entry:index>=0?structuredClone(gradesCache.entries[index]):{name:'',category:'core',countsForFinal:true,bonus:0,bonusKnown:false,parts:[{id:id(),name:tr('Zwischenprüfung','Midterm'),weight:20,value:null,estimate:null},{id:id(),name:tr('Schlussprüfung','Final exam'),weight:80,value:null,estimate:null}]}};
  }else if(action==='grade-draft-cancel'){gradeDraft=null;}
  else if(action==='grade-part-add'){gradeDraft.entry.parts.push({id:id(),name:tr('Neue Teilleistung','New assessment'),weight:10,value:null,estimate:null});}
  else if(action==='grade-part-remove'){gradeDraft.entry.parts.splice(Number(element.dataset.index),1);}
  else if(action==='grade-delete'){gradesCache.entries.splice(Number(element.dataset.index),1);gradeDraft=null;}
  else if(action==='simulation-edit'){
    const s=gradesCache.simulations.find(s=>s.id===activeSimulation),entry=simulationEntries(s).find(e=>MasterPlanGrades.key({...e,id:e.courseId})===element.dataset.key);
    gradeDraft={kind:'simulation',scenarioId:s.id,key:element.dataset.key,entry:structuredClone(entry)};
  }else if(action==='simulation-duplicate'){
    const s=gradesCache.simulations.find(s=>s.id===activeSimulation),copy=structuredClone(s);copy.id=id();copy.name+=' '+tr('(Kopie)','(copy)');gradesCache.simulations.push(copy);activeSimulation=copy.id;gradeDraft=null;
  }else if(action==='simulation-delete'){gradesCache.simulations=gradesCache.simulations.filter(s=>s.id!==activeSimulation);activeSimulation=null;gradeDraft=null;}
  render();$('#grade-editor')?.scrollIntoView({block:'start'});
}
function applyGradeDraft(){
  const e=gradeDraft.entry;
  if(!e.name.trim()||!MasterPlanGrades.forecast(e).valid)throw Error(tr('Bitte Titel, Noten und Gewichte prüfen.','Check title, grades and weights.'));
  if(gradeDraft.kind==='real'){
    const entry=structuredClone(e);entry.parts=entry.parts.map((p,i)=>({...p,id:p.id||`part-${i}`}));
    if(gradeDraft.index<0)gradesCache.entries.push(entry);else gradesCache.entries[gradeDraft.index]=entry;
  }else{
    const s=gradesCache.simulations.find(s=>s.id===gradeDraft.scenarioId);
    // Persist assumptions only; actual marks are read afresh from the real vault on every render.
    const entry=structuredClone(e);entry.parts=entry.parts.map(p=>({...p,value:null,actualLocked:undefined,structureLocked:undefined}));
    delete entry.actualMatched;delete entry.bonusLocked;s.entries[gradeDraft.key]=entry;
  }
  gradeDraft=null;render();notify(tr('Im Notenspeicher vorgemerkt – bitte verschlüsselt speichern.','Updated in memory – please save encrypted.'));
}

function settings() {
  return `${pageHeader(tr('Einstellungen & Datenspeicher','Settings & data storage'),tr('Kompakte lokale Daten, portable Sicherung und zweisprachige Oberfläche.','Compact local data, portable backup and bilingual UI.'))}
  <div class="grid columns-2"><div class="card"><h2 class="section-title">${tr('Speicherort','Storage folder')}</h2><p class="muted small">${tr('Wähle einen lokalen Ordner oder einen synchronisierten Cloud-Ordner (z. B. Nextcloud/OneDrive).','Choose a local folder or a cloud-synced folder (e.g. Nextcloud/OneDrive).')}</p><div id="folder-label" class="monospace tiny muted" style="overflow-wrap:anywhere">${tr('Lade Speicherort…','Loading storage path…')}</div><div class="actions" style="margin-top:16px">${button(tr('Datenordner verschieben','Move data folder'),'move-folder')}${button(tr('Bestehenden Ordner öffnen','Open existing folder'),'open-folder')}</div><div class="line"></div><p class="hint">${tr('Aus Sicherheitsgründen muss ein lokaler Ordnerpfad angegeben werden. Der Browser kann nicht automatisch auf deine Cloud zugreifen.','For security, provide a local folder path. The browser cannot automatically access your cloud.')}</p></div>
  <div class="card"><h2 class="section-title">${tr('Sicherung / Wiederherstellung','Backup / restore')}</h2><p class="muted small">${tr('Exportiert ausschließlich deine kompakten Studienpläne, keine VVZ-Kursdatenbank und keine Noten. Noten bleiben in grades.enc im gewählten Datenordner.','Exports compact study plans only, without the VVZ database or grades. Grades remain in grades.enc in your chosen data folder.')}</p><div class="actions">${button(tr('JSON exportieren','Export JSON'),'export-data','','button')}<label class="smallbtn" style="margin:0;cursor:pointer">${tr('JSON importieren','Import JSON')}<input type="file" accept=".json,application/json" id="import-file" hidden></label></div></div>
  <div class="card"><h2 class="section-title">${tr('Sprache & Darstellung','Language & appearance')}</h2><div class="row wrap"><button class="smallbtn" data-action="set-de">Deutsch</button><button class="smallbtn" data-action="set-en">English</button><button class="smallbtn" data-action="set-light">☀ Light</button><button class="smallbtn" data-action="set-dark">☾ Dark</button></div><div class="line"></div><div class="small muted">${tr('Schema-Version','Schema version')}: ${state.schema} · ${tr('Revision','Revision')}: ${state.revision}</div></div>
  <div class="card"><h2 class="section-title">${tr('Lokaler VVZ-Katalog','Offline VVZ catalogue')}</h2>
  <p class="small muted">${tr('Der ETH-Katalog wird einmalig heruntergeladen, automatisch indiziert und danach lokal durchsucht. Alle 24 Stunden werden nur die VVZ-Dump-Metadaten geprüft. Eine neue Datenbank wird ausschließlich bei einer Änderung geladen. Maximal eine externe Anfrage pro Minute – für Metadaten, Dump und Fallback zusammen.','The ETH catalogue is downloaded once and searched offline. Dump metadata is checked at most every 24 hours; only changes trigger a new download. One upstream request per minute at most, shared by all endpoints.')}</p>
  <div id="dump-status" class="small muted" style="overflow-wrap:anywhere">${escape(dumpStatus?.checking ? tr('Datenbank wird geprüft oder geladen…','Checking or downloading catalogue…') : dumpStatus?.available ? tr('Lokaler Katalog verfügbar','Offline catalogue ready') : tr('Noch kein lokaler Katalog vorhanden','No offline catalogue available yet'))}</div>
  <div class="actions" style="margin-top:14px">${button(tr('Jetzt nach Updates suchen','Check for updates'),'check-dump')}
  <a class="smallbtn" href="https://github.com/markbeep/vvzapi" target="_blank" rel="noopener noreferrer">VVZAPI</a></div>
  <p class="hint">${tr('Die heruntergeladene Datenbank liegt im separaten, von Git ignorierten Cache – nicht im persönlichen Cloud-Speicherordner.','The downloaded catalogue lives in a separate gitignored cache, outside your private cloud-synced folder.')}</p></div>
  <div class="card"><h2 class="section-title">${tr('Quellen & Datenschutz','Sources & privacy')}</h2><p class="small muted">MasterPlan ist keine offizielle ETH-Anwendung. Die Kursdaten stammen von der unabhängigen <a href="https://github.com/markbeep/vvzapi" target="_blank" rel="noopener noreferrer">VVZAPI</a>. Verbindlich sind deine geltenden <a href="https://ethz.ch/content/dam/ethz/special-interest/study-programme-websites/ms-compsci-and-eng-dam/documents/master-programme/MSc-CSE-Guidelines.pdf" target="_blank" rel="noopener noreferrer">MSc CSE Guidelines</a> und das ETH-Studienreglement.</p><p class="hint">${tr('Persönliche Daten bleiben lokal. VVZAPI liefert den Katalog-Dump; fehlende Wochenzeiten werden bei Bedarf direkt von ETH VVZ geladen und lokal zwischengespeichert.','Personal data stays local. VVZAPI supplies the catalogue dump; missing weekly slots are fetched from ETH VVZ on demand and cached locally.')}</p></div></div>`;
}

function fixed(c,p) {return c.locked || p.lockedSemesters.includes(c.semester);}
function askCourse(existing=null,semesterOverride=null,planKey=state.activePlan) {
  const p=getPlan(planKey); if(existing&&fixed(existing,p)){notify(tr('Zuerst Kurs/Semester entsperren.','Unlock course/semester first.'));return;}
  const title=prompt(tr('Modultitel','Course title'),existing?.title||''); if(title===null||!title.trim())return;
  const number=prompt(tr('Kursnummer (optional)','Course number (optional)'),existing?.number||'');if(number===null)return;
  const sem=prompt(tr('Semester: JJJJS für FS, JJJJW für HS','Semester: YYYYS for spring, YYYYW for autumn'),existing?.semester||semesterOverride||p.semesters[0]);if(sem===null)return;
  if(!/^\d{4}[SW]$/.test(sem)){notify(tr('Ungültiges Semesterformat, z. B. 2027S','Invalid semester, e.g. 2027S'));return;}
  if(p.lockedSemesters.includes(sem)){notify(tr('Das Zielsemester ist fixiert.','Target semester is locked.'));return;}
  const ects=prompt('ECTS',String(existing?.ects??0));if(ects===null)return;
  if(!Number.isFinite(Number(ects))||Number(ects)<0||Number(ects)>40){notify(tr('Ungültige ECTS','Invalid ECTS'));return;}
  const role=prompt(`${tr('Rolle','Role')}: ${roleList.join(', ')}`,existing?MasterPlanRules.allocationRole(existing):'extra');if(role===null)return;
  if(!roleList.includes(role)){notify(tr('Unbekannte Rolle','Unknown role'));return;}
  const status=prompt(`${tr('Status','Status')}: interested, planned, enrolled, completed`,existing?.status||'planned');if(status===null)return;
  if(!['interested','planned','enrolled','completed'].includes(status)){notify(tr('Ungültiger Status','Invalid status'));return;}
  const subtype=role==='specialisation-seminar'?'seminar':role==='specialisation'?prompt(tr('Art: lecture oder seminar','Type: lecture or seminar'),existing?.subtype||'lecture'):null;
  if(role==='specialisation'&&!['lecture','seminar'].includes(subtype))return notify(tr('Ungültige Spezialisierungsart.','Invalid specialisation type.'));
  const field=['specialisation','specialisation-seminar'].includes(role)?prompt(tr('Spezialisierungsgebiet (optional)','Specialisation field (optional)'),existing?.specialisation||p.specialisation||''):'';
  if(field===null)return;
  const usedForBSc=confirm(tr('Wurden diese Credits bereits für den Bachelorabschluss verwendet?','Were these credits already used for your Bachelor degree?'));
  const linked=existing?MasterPlanRules.resolveOffering(existing,sem):null;
  const record={...(existing||{}),...(linked||{}),id:existing?.id||id(),title:title.trim(),number:number||'',semester:sem,ects:Number(ects),...MasterPlanRules.allocationCategory(role),status,
    subtype:subtype||undefined,specialisation:field||undefined,usedForBSc,events:existing?.events||[]};
  return save(s=>{
    const pl=editPlan(s,p.id);
    if(pl.courses.some(c=>c.id!==record.id&&record.number&&String(c.number||'').trim().toUpperCase()===record.number.trim().toUpperCase()&&c.semester===sem))throw Error(tr('Kurs bereits im Semester zugeordnet.','Course already allocated to this semester.'));
    if(!pl.semesters.includes(sem))pl.semesters.push(sem);pl.semesters.sort();
    if(existing)pl.courses=pl.courses.map(c=>c.id===existing.id?record:c);else pl.courses.push(record);
    if(p.id!=='actual')return;
    const index=s.history.findIndex(c=>c.id===record.id);
    if(status==='completed'){if(index>=0)s.history[index]={...record,locked:true};else if(!s.history.some(c=>MasterPlanRules.allCourses({courses:[record]},[c]).length===1))s.history.push({...record,locked:true});}
    else if(index>=0)s.history.splice(index,1);
  });
}
function makeFromSearch(number,extra) {
  const result=results.find(x=>x.number===number);if(!result)return;
  const p=plan(), wanted=searchParams.semester!=='recent'?searchParams.semester:p.semesters[0];if(p.lockedSemesters.includes(wanted)){notify(tr('Semester ist fixiert.','Semester is locked.'));return;}
  if(p.courses.some(c=>c.number===number&&c.semester===wanted)){notify(tr('Modul existiert bereits in diesem Semester.','Course already added to that semester.'));return;}
  const role=extra?'extra':prompt(`${tr('Anrechnungskategorie','Credit category')}: core, specialisation, elective, extra, case, project, sip, thesis`,'elective');if(role===null)return;
  if(!roleList.includes(role)){notify(tr('Ungültige Kategorie','Invalid category'));return;}
  const off=result.offering||{};
  const c={id:id(),number,semester:wanted,title:(state.language==='en'?result.title_english||result.title:result.title||result.title_english)||number,ects:safe(result.credits),...MasterPlanRules.allocationCategory(role),status:'planned',unitId:off.unit_id||null,sourceSemester:off.source_semester||null,proxy:!!off.proxy,events:[],locked:false,creditApproved:extra?false:null};
  save(s=>{const pl=editPlan(s,p.id);if(!pl.semesters.includes(wanted)){pl.semesters.push(wanted);pl.semesters.sort();}pl.courses.push(c);});
}
function editEvents(course,planKey=state.activePlan) {
  const p=getPlan(planKey);if(fixed(course,p)){notify(tr('Modul oder Semester ist fixiert.','Course or semester locked.'));return;}
  const old=(course.events||[]).map(e=>`${e.day},${e.start},${e.end},${e.building||''},${e.floor||''},${e.room||''}`).join('\n');
  const response=prompt(tr('Ein Termin pro Zeile: Wochentag 0=Mo bis 6=So, Beginn, Ende, Gebäude, Stock, Raum (kommagetrennt)','One event per line: day 0=Mon to 6=Sun, start, end, building, floor, room (comma-separated)'),old);
  if(response===null)return;
  const lines=response.split('\n').filter(x=>x.trim());const events=[];
  for(const line of lines){const [day,start,end,building,floor,room]=line.split(',').map(x=>x.trim());if(!/^[0-6]$/.test(day)||!/^\d{2}:\d{2}$/.test(start)||!/^\d{2}:\d{2}$/.test(end)||start>=end){notify(tr('Ungültiger Termin.','Invalid event.'));return;}events.push({day:Number(day),start,end,building,floor,room,source:'manual'});}
  save(s=>{const x=editPlan(s,p.id).courses.find(z=>z.id===course.id);x.events=events;});
}
function formVal(form,name){return new FormData(form).get(name)?.toString().trim()||'';}
async function executeAction(action,element) {
  const p=getPlan(element.dataset.planId||state.activePlan), cid=element.dataset.id, course=p.courses.find(x=>x.id===cid);
  if(action==='course-details'){detailsBack=page;detailCourse={title:element.dataset.title,number:element.dataset.number,unitId:element.dataset.unitId?Number(element.dataset.unitId):null,sourceSemester:element.dataset.sourceSemester};changePage('course-details');await loadCourseDetails();return;}
  if(action==='close-details'){changePage(detailsBack);return;}
  if(action==='retry-details'){unitDetailsCache.delete(String(detailCourse.unitId));await loadCourseDetails();return;}
  if(action==='choose-schedule-module'){const form=$('#event-form');if(form&&course){form.elements.namedItem('course').value=course.id;$('#manual-vvz-link').innerHTML=courseLinks(course);document.querySelectorAll('[data-schedule-course]').forEach(e=>e.setAttribute('aria-pressed',String(e.dataset.scheduleCourse===course.id)));}return;}
  if(action==='place-slot'){fillScheduleSlot(element.dataset.day,element.dataset.start);return;}
  if(action==='shortlist-assign'){
    const result=results.find(c=>c.number===element.dataset.number);
    await executeAction('shortlist-result',element);
    const interest=state.interests.find(c=>c.number===element.dataset.number);
    if(interest)return executeAction('focus-assign',{dataset:{interestId:interest.id,planId:state.activePlan,sem:result?.offering?.source_semester||''}});
    return;
  }
  if(action==='reassign-course'){allocationEdit={planId:p.id,courseId:cid};render();$('#allocation-editor')?.scrollIntoView({block:'center'});return;}
  if(action==='cancel-reassignment'){allocationEdit=null;render();return;}
  if(action==='apply-reassignment'){
    const form=$('#reassign-form'),origin={...allocationEdit},target=formVal(form,'plan'),term=formVal(form,'semester'),role=formVal(form,'role');
    if(await save(s=>MasterPlanRules.moveAllocation(s,origin.planId,origin.courseId,target,term,role))){allocationEdit=null;render();}return;
  }
  if(action==='select-visible'){document.querySelectorAll('#assignment-choices input').forEach(e=>selectedInterests.add(e.value));refreshAssignmentChoices();return;}
  if(action==='clear-selection'){selectedInterests.clear();refreshAssignmentChoices();return;}
  if(action==='edit-scenario'){await save(s=>s.activePlan=cid);changePage('semesters');document.querySelector('#scenario-specialisation')?.scrollIntoView({block:'center'});return;}
  if(action==='focus-schedule-assign'){document.querySelector('#schedule-assignment')?.scrollIntoView({block:'center'});const form=$('#assign-course-form');if(form){form.elements.namedItem('plan').value=p.id;form.elements.namedItem('semester').value=schedule.current;refreshAssignmentChoices();}return;}
  if(action==='remove-semester'){
    const sem=element.dataset.sem;
    if(p.semesters.length<=1)return notify(tr('Mindestens ein Semester muss bleiben.','Keep at least one semester.'));
    if(p.lockedSemesters.includes(sem)||p.courses.some(c=>c.semester===sem&&c.locked))return notify(tr('Semester und Kurse zuerst entsperren.','Unlock the semester and its courses first.'));
    if(p.courses.some(c=>c.semester===sem)&&!confirm(tr('Semester und seine Zuweisungen entfernen? Merkliste und abgeschlossene Historie bleiben erhalten.','Remove this semester and its allocations? Shortlist and completed history are kept.')))return;
    return save(s=>{const dest=editPlan(s,p.id);dest.semesters=dest.semesters.filter(x=>x!==sem);dest.courses=dest.courses.filter(c=>c.semester!==sem);});
  }
  if(action==='catalog-prev')return runCatalogSearch(Math.max(0,catalogOffset-40));
  if(action==='catalog-next')return runCatalogSearch(catalogOffset+40);
  if(action==='browse-rw'){searchParams={...searchParams,programme:'cse-bsc',category:'requirement'};changePage('catalog');return;}
  if(action==='browse-eligible-core') {searchParams={...searchParams,programme:'eligible-core-all',category:'eligible-core'};changePage('catalog');return;}
  if(action==='shortlist-result'||action==='shortlist-extra'){const c=results.find(x=>x.number===element.dataset.number);if(!c)return;const name=state.language==='en'?(c.title_english||c.title):(c.title||c.title_english);const o=c.offering||{};return save(s=>{if(s.interests.some(x=>x.number===c.number))return;s.interests.push({id:id(),number:c.number,title:name||c.number,ects:safe(c.credits),suggestedRole:action==='shortlist-extra'?'extra':searchParams.category==='requirement'?'requirement':searchParams.category==='core'?'core':searchParams.category==='specialisation'?(/\bseminar\b/i.test(`${c.title||''} ${c.title_english||''}`)?'specialisation-seminar':'specialisation'):searchParams.category==='case'?'case':searchParams.category==='project'?'project':searchParams.category==='sip'?'sip':searchParams.category==='thesis'?'thesis':searchParams.category==='scientific'?'scientific':'elective',offerings:c.semesters||{},unitId:o.unit_id||null,sourceSemester:o.source_semester||null,reviewAvailable:c.rating!=null&&Number(c.rating)>0});});}
  if(action==='manual-interest'){const title=prompt(tr('Modultitel','Course title'));if(!title?.trim())return;const number=prompt(tr('Kursnummer (optional)','Course number (optional)'),'')||'';return save(s=>s.interests.push({id:id(),number,title:title.trim(),ects:0,suggestedRole:'extra',offerings:{}}));}
  if(action==='remove-interest')return save(s=>{s.interests=s.interests.filter(x=>x.id!==cid);});
  if(action==='focus-assign'){changePage('semesters');const form=$('#assign-course-form');if(element.dataset.planId)form.elements.namedItem('plan').value=element.dataset.planId;if(element.dataset.sem)form.elements.namedItem('semester').value=element.dataset.sem;if(element.dataset.interestId)selectedInterests.add(element.dataset.interestId);refreshAssignmentChoices();form.scrollIntoView({behavior:'smooth',block:'center'});return;}
  if(action==='assign-interest'){
    const form=$('#assign-course-form'),ids=[...selectedInterests],target=formVal(form,'plan'),term=formVal(form,'semester'),role=formVal(form,'role');
    if(await save(s=>MasterPlanRules.assignShortlist(s,target,term,ids,role,id))){selectedInterests.clear();refreshAssignmentChoices();}return;
  }
  if(action==='remove-course'){const key=element.dataset.planId||p.id,dest=getPlan(key),found=dest?.courses.find(x=>x.id===cid);if(!found)return;if(found.locked||dest.lockedSemesters.includes(found.semester))return notify(tr('Erst entsperren.','Unlock first.'));return save(s=>{editPlan(s,key).courses=editPlan(s,key).courses.filter(x=>x.id!==cid);});}
  if(action==='apply-vvz-slots'){const c=course, info=meetingData.get(String(c?.unitId));if(!c||!info||info.status!=='ready')return;const dest=getPlan(element.dataset.planId||p.id);if(fixed(c,dest))return notify(tr('Fixierter Kurs.','Course locked.'));const selected=[...document.querySelectorAll(`[data-slot="${CSS.escape(c.id)}"]:checked`)].map(e=>info.meetings[Number(e.value)]).filter(Boolean);return save(s=>{const item=editPlan(s,dest.id).courses.find(x=>x.id===c.id);item.events=[...(item.events||[]).filter(e=>!e.apiSlot),...selected.map(m=>({day:m.day,start:m.start,end:m.end,building:m.building||'',floor:m.floor||'',room:m.room||'',date:m.date||null,biweekly:!!m.biweekly,firstHalf:!!m.firstHalf,secondHalf:!!m.secondHalf,note:m.note||'',source:'vvz',apiSlot:m.slotKey,sourceSemester:item.sourceSemester}))];});}

  if(action==='go-semester-compare'){comparisonView='semesters';return changePage('plans');}
  if(action==='compare-view'){comparisonView=element.dataset.view==='semesters'?'semesters':'plans';return render();}
  if(action?.startsWith('go-'))return changePage(action.slice(3));
  if(action==='new-plan'){const name=prompt(tr('Name des neuen Plans','New plan name'),tr('Neuer Studienplan','New study plan'));if(!name?.trim())return;return save(s=>{const newId=id();s.plans.push({id:newId,name:name.trim(),specialisation:'',semesters:['2026W','2027S','2027W','2028S'],lockedSemesters:[],courses:[],notes:''});s.activePlan=newId;});}
  if(action==='open-plan')return save(s=>{s.activePlan=cid;});
  if(action==='duplicate-plan'){const x=state.plans.find(p=>p.id===cid);if(!x)return;const name=prompt(tr('Name der Kopie','Copy name'),`${x.name} Copy`);if(!name)return;return save(s=>{const n=structuredClone(x);n.id=id();n.name=name;s.plans.push(n);s.activePlan=n.id;});}
  if(action==='rename-plan'){const name=prompt(tr('Neuer Name','New name'),state.plans.find(p=>p.id===cid)?.name||'');if(!name?.trim())return;return save(s=>{s.plans.find(p=>p.id===cid).name=name.trim()});}
  if(action==='delete-plan'){if(state.plans.length<2)return notify(tr('Mindestens ein Plan muss bleiben.','At least one plan is required.'));if(!confirm(tr('Plan wirklich löschen?','Delete plan?')))return;return save(s=>{s.plans=s.plans.filter(p=>p.id!==cid);if(s.activePlan===cid)s.activePlan='actual';});}
  if(action==='add-semester'){let guess=p.semesters[p.semesters.length-1]||'2026W',next=guess.endsWith('W')?`${Number(guess.slice(0,4))+1}S`:`${guess.slice(0,4)}W`;const sem=prompt(tr('Semester (JJJJS / JJJJW)','Semester (YYYYS / YYYYW)'),next);if(!sem)return;if(!/^\d{4}[SW]$/.test(sem))return notify(tr('Ungültiges Semester','Invalid semester'));return save(s=>{const x=editPlan(s,p.id);if(!x.semesters.includes(sem)){x.semesters.push(sem);x.semesters.sort();}});}
  if(action==='lock-semester'){const sem=element.dataset.sem;return save(s=>{const list=editPlan(s,p.id).lockedSemesters;const i=list.indexOf(sem);if(i>=0)list.splice(i,1);else list.push(sem);});}
  if(action==='lock-course'){if(p.lockedSemesters.includes(course.semester))return notify(tr('Semester ist fixiert.','Semester locked.'));return save(s=>{editPlan(s,p.id).courses.find(c=>c.id===cid).locked=!course.locked;});}
  if(action==='manual-course')return askCourse(null,element.dataset.sem,element.dataset.planId||p.id);
  if(action==='edit-course')return askCourse(course,null,p.id);
  if(action==='add-result'||action==='add-extra')return makeFromSearch(element.dataset.number,action==='add-extra');
  if(action==='add-event'){changePage('schedule');return;}
  if(action==='edit-events')return editEvents(course,p.id);
  if(action==='check-dump'){try{dumpStatus=await request('/api/vvz/dump/check','POST',{});render();refreshDumpStatus();notify(tr('VVZ-Abgleich gestartet.','VVZ sync started.'));}catch(e){notify(e.message);}return;}
  if(action==='move-folder'||action==='open-folder'){const folder=prompt(tr('Absoluter lokaler Ordnerpfad (kann im Cloud-Sync-Ordner liegen)','Absolute local folder path (may reside in cloud-synced folder)'),$('#folder-label')?.textContent||'');if(!folder)return;try{const x=await request('/api/storage','POST',{mode:action==='move-folder'?'move':'open',folder});state=x.state;notify(tr('Datenordner aktualisiert.','Data folder updated.'));render();loadFolder();}catch(e){notify(e.message);}return;}
  if(action==='export-data'){const b=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),url=URL.createObjectURL(b),a=document.createElement('a');a.href=url;a.download='masterplan-export.json';a.click();URL.revokeObjectURL(url);return;}
  if(action==='lock-grades'){gradeDraft=null;gradesCache=null;gradesPassword=null;return render();}
  if(['grade-add','grade-edit','grade-delete','grade-draft-cancel','grade-part-add','grade-part-remove','simulation-edit','simulation-duplicate','simulation-delete'].includes(action))return privateAction(action,element);
  if(action==='grade-save'){try{await saveGrades();notify(tr('Noten verschlüsselt gespeichert.','Grades encrypted and saved.'));}catch(e){notify(e.message);}return;}
  if(action==='set-de'||action==='set-en')return save(s=>s.language=action==='set-de'?'de':'en');
  if(action==='set-light'||action==='set-dark')return save(s=>s.theme=action==='set-light'?'light':'dark');
}
async function refreshDumpStatus(){
  if(dumpStatusTimer){clearTimeout(dumpStatusTimer);dumpStatusTimer=null;}
  if(page!=='settings')return;
  try{
    dumpStatus=await request('/api/vvz/dump/status');
    const el=$('#dump-status');
    if(el){
      const phase={checking:tr('Prüfe Änderungsmetadaten…','Checking metadata…'),downloading:tr('Lade den VVZ-Dump herunter…','Downloading the VVZ dump…'),validating:tr('Prüfe SQLite-Datenbank…','Validating SQLite database…'),ready:tr('Lokale Datenbank einsatzbereit','Offline catalogue ready'),stale:tr('Lokale Datenbank wird weiterverwendet','Using the last valid offline catalogue'),missing:tr('Noch kein lokaler Katalog','No offline catalogue yet'),failed:tr('Erstdownload fehlgeschlagen','Initial download failed')}[dumpStatus.phase]||dumpStatus.phase;
      const last=dumpStatus.lastChecked?new Date(dumpStatus.lastChecked*1000).toLocaleString(state.language==='de'?'de-CH':'en-GB'):'—';
      el.textContent=`${phase} · ${dumpStatus.available?tr('Offline-Suche verfügbar','Offline search available'):tr('Fallback-API','Fallback API')} · ${tr('Letzte Prüfung','Last check')}: ${last}${dumpStatus.error?' · '+dumpStatus.error:''}`;
    }
    if(dumpStatus.checking&&page==='settings')dumpStatusTimer=setTimeout(refreshDumpStatus,3500);
  }catch(e){const el=$('#dump-status');if(el)el.textContent=e.message;}
}
async function loadFolder(){try{const x=await request('/api/storage');const e=$('#folder-label');if(e)e.textContent=x.folder;}catch(e){notify(e.message);}}
function base64(bytes){let b='';for(const x of bytes)b+=String.fromCharCode(x);return btoa(b);}
function unbase64(x){return Uint8Array.from(atob(x),x=>x.charCodeAt(0));}
async function gradeKey(password,salt){const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations:250000,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);}
async function unlockGrades(password){if(!globalThis.crypto?.subtle)throw Error(tr('Verschlüsselung benötigt einen sicheren Browserkontext.','Encryption requires a secure browser context.'));const payload=(await request('/api/grades')).encrypted;if(!payload){gradesCache={entries:[],simulations:[]};gradesPassword=password;return;}const salt=unbase64(payload.salt),iv=unbase64(payload.iv);const key=await gradeKey(password,salt);let plaintext;try{plaintext=await crypto.subtle.decrypt({name:'AES-GCM',iv},key,unbase64(payload.ciphertext));}catch{throw Error(tr('Falsches Passwort oder beschädigte Daten.','Wrong password or corrupt data.'));}const decoded=JSON.parse(new TextDecoder().decode(plaintext));gradesCache=MasterPlanGrades.validateVault(decoded);gradesPassword=password;}
let gradeSaveQueue=Promise.resolve();
function saveGrades(){if(!gradesCache||!gradesPassword)return Promise.reject(Error('Vault locked'));const snapshot=structuredClone(gradesCache),password=gradesPassword;const task=()=>persistGrades(snapshot,password);gradeSaveQueue=gradeSaveQueue.then(task,task);return gradeSaveQueue;}
async function persistGrades(snapshot,password){const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12)),key=await gradeKey(password,salt);const plaintext=new TextEncoder().encode(JSON.stringify(snapshot));const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,plaintext);await request('/api/grades','POST',{salt:base64(salt),iv:base64(iv),ciphertext:base64(new Uint8Array(ciphertext))});}

addEventListener('click',async event=>{const nav=event.target.closest('[data-nav]');if(nav)return changePage(nav.dataset.nav);const action=event.target.closest('[data-action]');if(action){event.preventDefault();try{await executeAction(action.dataset.action,action);}catch(e){notify(e.message);}return;}});
addEventListener('change',async event=>{const e=event.target;
  if(e.form?.id==='assign-course-form'){if(e.name==='interest'){if(e.checked)selectedInterests.add(e.value);else selectedInterests.delete(e.value);}refreshAssignmentChoices();return;}
  if(e.form?.id==='event-form'&&e.name==='course'){const course=plan().courses.find(c=>c.id===e.value);$('#manual-vvz-link').innerHTML=course?courseLinks(course):'';return;}
  if(e.form?.id==='search-form') {
    ++searchGeneration;results=[];searchState='';catalogOffset=0;catalogTotal=0;
    const form=e.form,cat=form.elements.namedItem('category'),prog=form.elements.namedItem('programme');
    if(cat.value==='eligible-core'&&!eligibleCoreSelection(prog.value))prog.value='eligible-core-all';
    if(prog.value==='eligible-core-all')cat.value='eligible-core';
    if(cat.value!=='eligible-core'&&prog.value==='eligible-core-all')prog.value='cse';
    searchParams={q:formVal(form,'q'),programme:prog.value,category:cat.value,semester:[formVal(form,'semester'),formVal(form,'semester2')].filter((v,i,a)=>v&&a.indexOf(v)===i).join(',')};
    if(e.name!=='q')render();return;
  }
if(e.id==='compare-left-plan'||e.id==='compare-right-plan'){const side=e.id==='compare-left-plan'?'left':'right';comparison[side+'Plan']=e.value;const selected=getPlan(e.value);comparison[side+'Semester']=selected?.semesters.includes(comparison[side+'Semester'])?comparison[side+'Semester']:(selected?.semesters.includes(comparison[side==='left'?'rightSemester':'leftSemester'])?comparison[side==='left'?'rightSemester':'leftSemester']:selected?.semesters[0]||null);render();return;}if(e.id==='compare-left-sem'||e.id==='compare-right-sem'){comparison[e.id==='compare-left-sem'?'leftSemester':'rightSemester']=e.value;render();return;}if(e.dataset.change==='active-plan'){await save(s=>s.activePlan=e.value);return;}if(e.id==='schedule-sem'){schedule.current=e.value;assignmentContext=null;render();void syncMeetingOptions();return;}if(e.id==='scenario-specialisation'){await save(s=>{editPlan(s,s.activePlan).specialisation=e.value;});return;}if(e.id==='bsc-scientific'){await save(s=>{s.scientificWorksBSc=e.checked;});return;}if(e.dataset.spec){await save(s=>{const i=s.selectedSpecialisations.indexOf(e.dataset.spec);if(e.checked&&i<0)s.selectedSpecialisations.push(e.dataset.spec);if(!e.checked&&i>=0)s.selectedSpecialisations.splice(i,1);});return;}if(e.id==='import-file'&&e.files?.[0]){try{if(e.files[0].size>2_000_000)throw Error('File too large');const value=JSON.parse(await e.files[0].text());if(!confirm(tr('Bestehende Pläne ersetzen?','Replace existing plans?')))return;state=await request('/api/import','POST',value);render();notify(tr('Importiert.','Imported.'));}catch(err){notify(err.message);}}});
addEventListener('submit',async event=>{const form=event.target;if(form.id==='assign-course-form'){event.preventDefault();return;}if(form.id==='search-form'){event.preventDefault();searchParams={q:formVal(form,'q'),programme:formVal(form,'programme'),category:formVal(form,'category'),semester:[formVal(form,'semester'),formVal(form,'semester2')].filter((v,i,a)=>v&&a.indexOf(v)===i).join(',')};await runCatalogSearch();return;}if(form.id==='event-form'){event.preventDefault();const p=plan(),selected=formVal(form,'course'),c=p.courses.find(x=>x.id===selected);if(!c)return notify(tr('Kurs auswählen.','Choose course.'));if(fixed(c,p))return notify(tr('Kurs oder Semester fixiert.','Course or semester locked.'));const day=Number(formVal(form,'day')),start=formVal(form,'start'),end=formVal(form,'end');if(!(day>=0&&day<=6&&/^\d{2}:\d{2}$/.test(start)&&/^\d{2}:\d{2}$/.test(end)&&start<end))return notify(tr('Ungültiger Termin.','Invalid time.'));await save(s=>{editPlan(s,p.id).courses.find(x=>x.id===c.id).events.push({day,start,end,building:formVal(form,'building'),floor:formVal(form,'floor'),room:formVal(form,'room'),source:'manual'});});return;}if(form.id==='grades-unlock-form'){event.preventDefault();const password=formVal(form,'password');try{await unlockGrades(password);render();}catch(e){notify(e.message);}return;}});
$('#lang-toggle').addEventListener('click',()=>save(s=>s.language=s.language==='de'?'en':'de'));
$('#theme-toggle').addEventListener('click',()=>save(s=>s.theme=s.theme==='light'?'dark':'light'));
$('#menu-toggle').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
(async()=>{try{state=await request('/api/state');guidelines=await request('/api/guidelines').catch(()=>null);render();updateStatus(tr('Lokal gespeichert','Saved locally'));if(page==='settings'){loadFolder();refreshDumpStatus();}}catch(e){$('#app').innerHTML=`<div class="card">${escape(e.message)}</div>`;}})();

addEventListener('input',event=>{if(event.target.form?.id==='assign-course-form'&&event.target.name==='filter')refreshAssignmentChoices();});
let draggedAllocation=null;
addEventListener('dragstart',event=>{
  if(event.target.closest('[data-schedule-course]'))return;const card=event.target.closest('[data-drag-course]');if(!card||card.draggable!==true){event.preventDefault();return;}
  draggedAllocation={planId:card.dataset.dragPlan,courseId:card.dataset.dragCourse};
  event.dataTransfer.setData('application/x-masterplan-course',JSON.stringify(draggedAllocation));event.dataTransfer.effectAllowed='move';
});
addEventListener('dragend',()=>{draggedAllocation=null;document.querySelectorAll('.drop-target').forEach(e=>e.classList.remove('drop-target'));});
addEventListener('dragover',event=>{const target=event.target.closest('[data-drop-plan]');if(!target||!draggedAllocation)return;event.preventDefault();event.dataTransfer.dropEffect='move';target.classList.add('drop-target');});
addEventListener('dragleave',event=>{const target=event.target.closest('[data-drop-plan]');if(target&&!target.contains(event.relatedTarget))target.classList.remove('drop-target');});
addEventListener('drop',async event=>{
  const target=event.target.closest('[data-drop-plan]'),source=draggedAllocation;if(!target||!source)return;
  event.preventDefault();draggedAllocation=null;target.classList.remove('drop-target');
  const p=getPlan(source.planId),c=p.courses.find(c=>c.id===source.courseId);
  if(c&&source.planId===target.dataset.dropPlan&&c.semester===target.dataset.dropSem)return;
  await save(s=>MasterPlanRules.moveAllocation(s,source.planId,source.courseId,target.dataset.dropPlan,target.dataset.dropSem));
});

function fillScheduleSlot(day,start,courseId=null){
  const form=$('#event-form');if(!form)return notify(tr('Zuerst ein Modul diesem Semester zuweisen.','Assign a module to this semester first.'));
  if(courseId)form.elements.namedItem('course').value=courseId;
  const course=plan().courses.find(c=>c.id===formVal(form,'course'));
  if(!course||course.semester!==schedule.current||fixed(course,plan()))return notify(tr('Modul nicht verfügbar oder gesperrt.','Module unavailable or locked.'));
  form.elements.namedItem('day').value=day;form.elements.namedItem('start').value=start;
  form.elements.namedItem('end').value=`${String(Math.min(23,Number(start.slice(0,2))+1)).padStart(2,'0')}:${start.slice(3)}`;
  $('#manual-vvz-link').innerHTML=courseLinks(course);form.scrollIntoView({block:'center',behavior:'smooth'});form.elements.namedItem('start').focus();
}
let draggedScheduleCourse=null;
addEventListener('dragstart',event=>{const item=event.target.closest('[data-schedule-course]');if(!item)return;if(!item.draggable){event.preventDefault();return;}draggedScheduleCourse=item.dataset.scheduleCourse;event.dataTransfer.setData('application/x-masterplan-meeting',draggedScheduleCourse);event.dataTransfer.effectAllowed='copy';});
addEventListener('dragover',event=>{if(draggedScheduleCourse&&event.target.closest('.daycell')){event.preventDefault();event.dataTransfer.dropEffect='copy';}});
addEventListener('drop',event=>{const cell=event.target.closest('.daycell');if(!cell||!draggedScheduleCourse)return;event.preventDefault();fillScheduleSlot(cell.dataset.day,cell.dataset.start,draggedScheduleCourse);draggedScheduleCourse=null;});
addEventListener('dragend',()=>draggedScheduleCourse=null);
addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('.daycell')){event.preventDefault();fillScheduleSlot(event.target.dataset.day,event.target.dataset.start);}});

addEventListener('input',event=>{
  const e=event.target;if(!e.matches('[data-grade-input]')||!gradeDraft)return;
  const field=e.dataset.gradeInput,index=e.dataset.gradePart;
  if(index!=null){const part=gradeDraft.entry.parts[Number(index)];if(!part)return;
    if(gradeDraft.kind==='simulation'&&(field==='value'||part.structureLocked&&['name','weight'].includes(field)||part.actualLocked))return;
    part[field]=['value','estimate','weight'].includes(field)?privateNumber(e.value):e.value;
    if(field==='value'){const estimate=e.closest('tr').querySelector('[data-grade-input="estimate"]');if(estimate)estimate.disabled=part.value!=null;}
  }else if(field==='category'){const category=MasterPlanRules.allocationCategory(e.value);gradeDraft.entry.category=category.role;gradeDraft.entry.subtype=category.subtype;gradeDraft.entry.countsForFinal=e.value!=='excluded'&&e.value!=='specialisation-seminar';}
  else if(field==='countsForFinal')gradeDraft.entry.countsForFinal=e.checked;
  else if(field==='bonus'&&gradeDraft.entry.bonusLocked)return;
  else {gradeDraft.entry[field]=['bonus','targetGrade'].includes(field)?privateNumber(e.value):e.value;if(field==='bonus'&&gradeDraft.kind==='real')gradeDraft.entry.bonusKnown=true;}
  const preview=$('#grade-preview');if(preview)preview.innerHTML=forecastHtml(gradeDraft.entry);
});
addEventListener('change',event=>{
  const e=event.target;
  if(e.matches('[data-grade-link]')&&gradeDraft){const c=allCourses(actual()).find(c=>c.id===e.value);if(c){gradeDraft.entry={...gradeDraft.entry,...MasterPlanGrades.baseEntry(c),parts:gradeDraft.entry.parts,bonus:gradeDraft.entry.bonus??0};render();}else{delete gradeDraft.entry.courseId;delete gradeDraft.entry.number;}}
  if(e.id==='simulation-select'){activeSimulation=e.value;gradeDraft=null;render();}
  if(e.id==='simulation-plan'){const s=gradesCache?.simulations.find(s=>s.id===activeSimulation);if(s){s.planId=e.value;gradeDraft=null;render();}}
});
addEventListener('submit',event=>{
  const form=event.target;
  if(form.id==='simulation-create-form'){event.preventDefault();const name=formVal(form,'name');if(!name||!gradesCache)return;const s={id:id(),name,planId:state.activePlan,entries:{}};gradesCache.simulations.push(s);activeSimulation=s.id;gradeDraft=null;render();}
  if(form.id==='grade-entry-form'){event.preventDefault();try{applyGradeDraft();}catch(e){notify(e.message);}}
});
