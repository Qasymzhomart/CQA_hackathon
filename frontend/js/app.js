"use strict";
const BASE = localStorage.getItem("cqa_api_base") || "http://localhost:8000";
const state={conversations:[],evaluations:{},appeals:[],checklist:[],current:null,pendingAppeal:null};
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api=async(path,options={})=>{
 const res=await fetch(BASE+path,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw new Error(typeof data.detail==="string"?data.detail:JSON.stringify(data.detail||data));
 return data;
};
const notify=(message,error=false)=>{const n=$("#alert");n.textContent=message;n.className=error?"notice error":"notice";clearTimeout(notify.timer);notify.timer=setTimeout(()=>{n.textContent="";n.className=""},6000)};
const view=name=>{document.querySelectorAll(".page").forEach(x=>x.classList.toggle("active",x.id===name));document.querySelectorAll(".nav").forEach(x=>x.classList.toggle("active",x.dataset.view===name));window.scrollTo({top:0,behavior:"smooth"});if(name==="reviews")loadReviews();if(name==="checklist")loadChecklist()};
const statusLabel=s=>({"not evaluated":"Не оценен",evaluated:"Оценен",appealed:"Апелляция",reviewed:"Проверен"}[s]||s);
const criterionById=id=>state.checklist.find(c=>c.id===id)||{id,name:id,weight:0,scale_max:1,response_type:"binary"};
const langChannel=c=>c.channel==="voice_call"?"Звонок":"Чат";
async function initialize(){
 try{const [cs,es,cl]=await Promise.all([api("/api/conversations"),api("/api/evaluations"),api("/api/checklist")]);state.conversations=cs;state.checklist=cl.criteria;state.evaluations={};for(const e of es)state.evaluations[e.conversation_id]=e;renderDashboard()}catch(e){notify("Не удалось подключиться к backend: "+e.message,true);renderDashboard()}
}
function renderDashboard(){
 const cs=state.conversations;
 const filt=cs.filter(c=>(!$("#search").value||c.conversation_id.toLowerCase().includes($("#search").value.toLowerCase()))&&(!$("#lang").value||c.language===$("#lang").value)&&(!$("#channel").value||c.channel===$("#channel").value)&&(!$("#status").value||((state.evaluations[c.conversation_id]?.status)||"not evaluated")===$("#status").value));
 const evals=Object.values(state.evaluations);
 $("#stats").innerHTML=[["Всего диалогов",cs.length],["Оценено",evals.length],["Средний балл",evals.length?(evals.reduce((a,e)=>a+Number(e.final_score||0),0)/evals.length).toFixed(1):"—"],["Апелляции",evals.filter(x=>x.status==="appealed").length]].map(([k,v])=>'<div class="stat"><strong>'+esc(v)+'</strong><span>'+esc(k)+'</span></div>').join("");
 $("#conversationRows").innerHTML=filt.map(c=>{const e=state.evaluations[c.conversation_id],status=e?.status||"not evaluated";return '<tr><td>'+esc(c.conversation_id)+'</td><td><span class="tag">'+esc(c.language)+'</span></td><td>'+esc(langChannel(c))+'</td><td><strong>'+(e?esc(e.final_score)+" / 100":"—")+'</strong></td><td><span class="tag '+(status==="appealed"?"warn":status==="not evaluated"?"gray":"")+'">'+statusLabel(status)+'</span></td><td><button class="btn small secondary" data-open="'+esc(c.conversation_id)+'">Открыть →</button></td></tr>'}).join("")||'<tr><td colspan="6" class="empty">Диалогов нет. Загрузите демо или импортируйте JSON.</td></tr>';
 document.querySelectorAll("[data-open]").forEach(b=>b.onclick=()=>openConversation(b.dataset.open));
}
async function openConversation(id){
 try{const c=await api("/api/conversations/"+encodeURIComponent(id));state.current=c;$("#conversationTitle").textContent=c.conversation_id;$("#conversationMeta").textContent=c.language+" · "+langChannel(c);$("#messageCount").textContent=c.transcript.length+" сообщений";
 $("#messages").innerHTML=c.transcript.map((m,i)=>'<div class="message '+esc(m.speaker.toLowerCase()==="agent"?"operator":m.speaker.toLowerCase())+'" id="message-M'+(i+1)+'"><div class="msghead"><span>M'+(i+1)+' · '+esc(m.speaker.toUpperCase())+'</span><span>'+esc(m.timestamp)+'</span></div><p>'+esc(m.text)+'</p></div>').join("");
 $("#audioBlock").innerHTML=c.audio_url&&/^https?:\/\//.test(c.audio_url)?'<p><a href="'+esc(c.audio_url)+'" target="_blank" rel="noopener noreferrer">Открыть запись звонка ↗</a></p><audio controls src="'+esc(c.audio_url)+'"></audio>':"";
 view("conversation");renderEvaluation(state.evaluations[id]);
 }catch(e){notify("Не удалось открыть: "+e.message,true)}
}
function jumpEvidence(text){
 const match=String(text).match(/\bM(\d+)\b/i);if(!match){notify("Для доказательства нет номера реплики",true);return}
 const el=$("#message-M"+match[1]);if(!el){notify("Реплика не найдена",true);return}el.scrollIntoView({behavior:"smooth",block:"center"});el.classList.add("highlight");setTimeout(()=>el.classList.remove("highlight"),2800)
}
function renderEvaluation(e){
 if(!e){$("#evalMethod").textContent="";$("#evaluationBody").className="empty";$("#evaluationBody").textContent="Пока нет оценки. Нажмите «Запустить оценку».";return}
 const results=e.results||[],rows=e.criteria||[];$("#evalMethod").textContent=e.assessment_method==="demo_heuristics"?"Эвристика · DEMO":"Backend";
 const gross=e.gross_errors||[];$("#evaluationBody").className="";
 $("#evaluationBody").innerHTML='<div class="scorehero"><div><small>ИТОГОВАЯ ОЦЕНКА</small><strong>'+esc(Number(e.final_score).toFixed(2))+' <small style="display:inline">/100</small></strong></div><div class="hintscore">'+esc(statusLabel(e.status))+'<br>'+ (gross.length?'<span class="dangertext">Критическая ошибка</span>':'Без выявленных грубых ошибок')+'</div></div><div class="criteria">'+results.map(r=>{
 const c=criterionById(r.criterion_id),detail=rows.find(x=>x.criterion_id===r.criterion_id);const na=!!r.na;const flag=c.response_type==="flag";const val=flag?(r.raw_score>0?"ДА":"НЕТ"):na?"N/A":r.raw_score+" / "+c.scale_max;
 const ev=(r.evidence||[]).map(v=>'<button class="evidence" data-evidence="'+esc(v)+'">↗ '+esc(v)+'</button>').join("");
 return '<article class="criterion"><div class="criterionheader"><h3>'+esc(c.name)+'</h3><span class="tag '+(na?"warn":"")+'">'+esc(val)+'</span></div><p>'+esc(r.explanation)+'</p>'+(na?'<p class="na">N/A: '+esc(r.na_reason||"Критерий неприменим")+'</p>':"")+(ev||'<p class="muted">Нет прямого доказательства</p>')+'<div class="critfoot"><span class="critmeta">'+(flag?"Отдельный флаг":na?"Исключен из расчёта":"Вес "+c.weight+"% · вклад "+Number(detail?.contribution??0).toFixed(2))+'</span><button class="btn small secondary" data-appeal="'+esc(r.criterion_id)+'">Апелляция</button></div></article>'
 }).join("")+'</div>';
 document.querySelectorAll("[data-evidence]").forEach(b=>b.onclick=()=>jumpEvidence(b.dataset.evidence));
 document.querySelectorAll("[data-appeal]").forEach(b=>b.onclick=()=>startAppeal(b.dataset.appeal));
}
async function evaluate(){
 if(!state.current)return;
 const b=$("#evaluateBtn");b.disabled=true;b.textContent="Оцениваем…";
 try{const e=await api("/api/ai/evaluate/"+encodeURIComponent(state.current.conversation_id),{method:"POST"});state.evaluations[e.conversation_id]=e;renderEvaluation(e);renderDashboard();notify("AI-оценка Gemini выполнена.")}catch(e){notify("Ошибка AI-оценки: "+e.message,true)}finally{b.disabled=false;b.textContent="▶ Запустить оценку"}
}
function startAppeal(id){
 const e=state.evaluations[state.current?.conversation_id];if(!e){notify("Сначала оцените диалог",true);return}
 state.pendingAppeal={evaluation_id:e.evaluation_id,criterion_id:id};$("#appealTarget").textContent=criterionById(id).name+" · Исходная оценка: "+(e.results.find(x=>x.criterion_id===id)?.raw_score??"—");$("#appealComment").value="";$("#appealModal").showModal()
}
async function submitAppeal(event){event.preventDefault();const comment=$("#appealComment").value.trim();if(!comment)return;try{const appeal=await api("/api/appeals",{method:"POST",body:JSON.stringify({...state.pendingAppeal,comment})});const e=state.evaluations[state.current.conversation_id];e.status="appealed";state.appeals.push(appeal);$("#appealModal").close();renderEvaluation(e);renderDashboard();notify("Апелляция сохранена")}catch(e){notify("Ошибка апелляции: "+e.message,true)}}
async function loadReviews(){
 try{const [appeals,es]=await Promise.all([api("/api/appeals"),api("/api/evaluations")]);state.appeals=appeals;state.evaluations={};es.forEach(e=>state.evaluations[e.conversation_id]=e);renderDashboard();
 $("#reviewList").innerHTML=appeals.map(a=>{
 const e=es.find(x=>x.evaluation_id===a.evaluation_id),r=e?.results.find(x=>x.criterion_id===a.criterion_id),c=criterionById(a.criterion_id);
 return '<article class="reviewcard"><h3>'+esc(e?.conversation_id||a.evaluation_id)+' · '+esc(c.name)+'</h3><span class="tag '+(a.status==="open"?"warn":"")+'">'+esc(a.status)+'</span><p><b>Комментарий:</b> '+esc(a.comment)+'</p><p><b>Исходная оценка:</b> '+esc(r?.raw_score??"—")+' / '+esc(c.scale_max)+' · <b>Итог:</b> '+esc(e?.final_score??"—")+'</p><p>'+esc(r?.explanation||"")+'</p><div class="reviewcontrols"><label>Баллы <input type="number" min="0" max="'+esc(c.scale_max)+'" step="any" id="score-'+esc(a.appeal_id)+'" value="'+esc(r?.raw_score??0)+'"/></label><label>Основание решения <input id="reason-'+esc(a.appeal_id)+'" placeholder="Причина изменения или подтверждения" /></label><button class="btn secondary" data-confirm="'+esc(a.appeal_id)+'">Подтвердить</button><button class="btn primary" data-change="'+esc(a.appeal_id)+'">Изменить</button></div></article>'
 }).join("")||'<div class="panel empty">Апелляций пока нет</div>';
 document.querySelectorAll("[data-confirm],[data-change]").forEach(b=>b.onclick=()=>reviewAppeal(b.dataset.confirm||b.dataset.change,!!b.dataset.change));
 }catch(e){notify("Ошибка загрузки апелляций: "+e.message,true)}
}
async function reviewAppeal(id,change){
 const a=state.appeals.find(x=>x.appeal_id===id),e=Object.values(state.evaluations).find(x=>x.evaluation_id===a?.evaluation_id);if(!a||!e)return;
 const r=e.results.find(x=>x.criterion_id===a.criterion_id),c=criterionById(a.criterion_id);
 const value=change?Number(document.getElementById("score-"+id).value):r?.raw_score;
 const reason=document.getElementById("reason-"+id).value.trim();
 if(!reason){notify("Укажите причину решения проверяющего",true);return}
 if(!Number.isFinite(value)||value<0||value>c.scale_max){notify("Баллы вне допустимого диапазона",true);return}
 try{const updated=await api("/api/reviews",{method:"POST",body:JSON.stringify({evaluation_id:e.evaluation_id,criterion_id:a.criterion_id,confirmed_score:value,reviewer_comment:reason})});state.evaluations[updated.conversation_id]=updated;notify("Решение принято. Новый итог: "+updated.final_score);await loadReviews()}catch(err){notify("Ошибка решения: "+err.message,true)}
}
async function loadChecklist(){try{const d=await api("/api/checklist");state.checklist=d.criteria;renderEditor()}catch(e){notify("Не удалось получить чек-лист: "+e.message,true)}}
function renderEditor(){
 $("#weightInfo").textContent="Сумма оцениваемых весов должна быть ровно 100%. Грубые ошибки — отдельный флаг.";
 $("#criteriaEditor").innerHTML=state.checklist.map((c,i)=>'<div class="editorcard" data-index="'+i+'"><label>Название <input data-field="name" value="'+esc(c.name)+'"/></label><label>Описание <input data-field="description" value="'+esc(c.description||"")+'"/></label><label>Вес % <input type="number" min="0" max="100" data-field="weight" value="'+esc(c.weight)+'"/></label><label>Тип <select data-field="response_type"><option value="binary" '+(c.response_type==="binary"?"selected":"")+'>Да / Нет</option><option value="scale" '+(c.response_type==="scale"?"selected":"")+'>Шкала</option><option value="flag" '+(c.response_type==="flag"?"selected":"")+'>Флаг</option></select></label><label>Максимум <input type="number" min="1" step="1" data-field="scale_max" value="'+esc(c.scale_max)+'"/></label><label class="check">N/A <input type="checkbox" data-field="allow_na" '+(c.allow_na?"checked":"")+'/></label><button class="btn small secondary" data-delete="'+i+'">Удалить</button></div>').join("");
 document.querySelectorAll("[data-delete]").forEach(b=>b.onclick=()=>{syncEditor();state.checklist.splice(Number(b.dataset.delete),1);renderEditor()})
}
function syncEditor(){
 document.querySelectorAll(".editorcard").forEach(el=>{const c=state.checklist[Number(el.dataset.index)];if(!c)return;for(const field of ["name","description","weight","response_type","scale_max","allow_na"]){const v=el.querySelector('[data-field="'+field+'"]');c[field]=field==="allow_na"?v.checked:field==="weight"||field==="scale_max"?Number(v.value):v.value}});
}
async function saveChecklist(){
 syncEditor();const ids=state.checklist.map(c=>c.id);if(new Set(ids).size!==ids.length){notify("ID критериев не должны повторяться",true);return}
 const sum=state.checklist.filter(c=>c.response_type!=="flag").reduce((a,c)=>a+c.weight,0);
 if(Math.abs(sum-100)>.001){notify("Сумма весов: "+sum+"%. Требуется 100%.",true);return}
 try{const d=await api("/api/checklist",{method:"PUT",body:JSON.stringify(state.checklist)});state.checklist=d.criteria;renderEditor();notify("Чек-лист сохранен в backend. Запустите оценку заново.")}catch(e){notify("Ошибка сохранения: "+e.message,true)}
}
const demo=[
 {conversation_id:"DEMO-RU-001",language:"RU",channel:"agent_chat",audio_url:null,transcript:[{timestamp:"00:02",speaker:"client",text:"Здравствуйте, где взять отчет по счету?"},{timestamp:"00:07",speaker:"operator",text:"Здравствуйте! Меня зовут Алина. Помогу вам. Уточните, за какой период?"},{timestamp:"00:16",speaker:"client",text:"За октябрь."},{timestamp:"00:21",speaker:"operator",text:"Откройте раздел Отчеты, выберите октябрь и нажмите Скачать."},{timestamp:"00:32",speaker:"operator",text:"Спасибо за обращение, до свидания!"}]},
 {conversation_id:"DEMO-KZ-001",language:"KZ",channel:"agent_chat",audio_url:null,transcript:[{timestamp:"00:03",speaker:"client",text:"Сәлеметсіз бе! Маған шот бойынша анықтама қажет."},{timestamp:"00:08",speaker:"operator",text:"Сәлеметсіз бе! Мен Айданамын, көмектесемін. Қай кезеңге керек?"},{timestamp:"00:15",speaker:"client",text:"Қазан айына."},{timestamp:"00:22",speaker:"operator",text:"Есептер бөлімін ашыңыз, қазан айын таңдаңыз. Рахмет!"}]},
 {conversation_id:"DEMO-EN-001",language:"EN",channel:"voice_call",audio_url:null,transcript:[{timestamp:"2026-11-07T10:00:01+05:00",speaker:"client",text:"Hello, I need my account statement."},{timestamp:"2026-11-07T10:00:04+05:00",speaker:"operator",text:"Hello! My name is Alex, happy to help. Which month?"},{timestamp:"2026-11-07T10:00:14+05:00",speaker:"client",text:"October."},{timestamp:"2026-11-07T10:00:20+05:00",speaker:"operator",text:"Open Reports, select October and click Download. Thank you, goodbye!"}]}
];
async function importRecords(records){
 const normalized=records.map(r=>({...r,channel:r.channel==="agent chat"?"agent_chat":r.channel==="voice call"?"voice_call":r.channel,transcript:(r.transcript||[]).map(m=>({timestamp:String(m.timestamp||""),speaker:m.speaker==="agent"?"operator":m.speaker,text:String(m.text||"")}))}));
 const r=await api("/api/conversations/import",{method:"POST",body:JSON.stringify(normalized)});notify("Импортировано: "+r.imported);await initialize()
}
document.querySelectorAll("[data-view]").forEach(b=>b.onclick=()=>view(b.dataset.view));
["search","lang","channel","status"].forEach(id=>document.getElementById(id).addEventListener(id==="search"?"input":"change",renderDashboard));
$("#backBtn").onclick=()=>view("dashboard");$("#evaluateBtn").onclick=evaluate;$("#refreshReviews").onclick=loadReviews;$("#saveChecklist").onclick=saveChecklist;
$("#addCriterion").onclick=()=>{syncEditor();state.checklist.push({id:"custom_"+Date.now(),name:"Новый критерий",description:"",weight:0,response_type:"binary",allow_na:false,scale_max:1});renderEditor()};
$("#demoBtn").onclick=async()=>{try{await importRecords(demo)}catch(e){notify("Ошибка загрузки демо: "+e.message,true)}};
$("#importBtn").onclick=()=>$("#jsonFile").click();
$("#jsonFile").onchange=async e=>{const file=e.target.files[0];if(!file)return;try{const obj=JSON.parse(await file.text());const records=Array.isArray(obj)?obj:obj.data?.records||obj.records;if(!Array.isArray(records))throw Error("Ожидается JSON-массив или data.records");await importRecords(records)}catch(err){notify("Импорт не удался: "+err.message,true)}finally{e.target.value=""}};
$("#appealCancel").onclick=()=>$("#appealModal").close();$("#appealForm").onsubmit=submitAppeal;
initialize();
