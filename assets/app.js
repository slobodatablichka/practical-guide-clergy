'use strict';

let tickets=[];
let topics=[];
let answers=[];
let answersByTopic=new Map();
let topicsById=new Map();
let selectedTicket=null;
let ticketAnswersVisible=false;

const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function normalize(s){
  return String(s??'').toLowerCase().replace(/ё/g,'е').replace(/[^а-яa-z0-9]+/gi,' ').replace(/\s+/g,' ').trim();
}

function tokenStem(w){
  const suffixes=['иями','ями','ами','ение','ения','ений','ание','ания','аний','ского','скому','скими','ская','ское','ские','остью','ости','ов','ев','ами','ями','ого','ему','ами','ах','ях','ый','ий','ая','ое','ые','ую','юю','ом','ем','ам','ям','а','я','ы','и','у','ю','е'];
  if(w.length<5)return w;
  for(const s of suffixes){if(w.length-s.length>=4&&w.endsWith(s))return w.slice(0,-s.length)}
  return w;
}

function distance(a,b,max=2){
  if(Math.abs(a.length-b.length)>max)return max+1;
  const prev=Array.from({length:b.length+1},(_,i)=>i);
  for(let i=1;i<=a.length;i++){
    let cur=[i], rowMin=i;
    for(let j=1;j<=b.length;j++){
      cur[j]=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
      rowMin=Math.min(rowMin,cur[j]);
    }
    if(rowMin>max)return max+1;
    for(let j=0;j<cur.length;j++)prev[j]=cur[j];
  }
  return prev[b.length];
}

function showView(name){
  document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden'));
  $(name+'View').classList.remove('hidden');
  document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.view===name));
  if(name==='search')setTimeout(()=>$('searchInput').focus(),0);
  history.replaceState(null,'','#'+name);
}

function ticketRefs(topic){
  return (topic.ticket_refs||[]).map(r=>`№${r.ticket}.${r.position}`).join(', ');
}

function readerLinks(obj){
  const refs=obj.book_refs&&obj.book_refs.length?obj.book_refs:[{reader_href:obj.reader_href,section_title:obj.book_section_title,book_order:obj.book_order}];
  const unique=[]; const seen=new Set();
  for(const r of refs){if(!r.reader_href||seen.has(r.reader_href))continue;seen.add(r.reader_href);unique.push(r)}
  return `<div class="reader-links">${unique.map((r,i)=>`<a class="reader-link ${i?'secondary':''}" href="${esc(r.reader_href)}">${i?'Связанный раздел':'Подробнее в учебнике'}${unique.length>1?` · #${String(r.book_order||'').padStart(3,'0')}`:''}</a>`).join('')}</div>`;
}

function answerBlock(row){
  const ans=answersByTopic.get(row.topic_id);
  const topic=topicsById.get(row.topic_id)||row;
  if(!ans)return '<div class="answer-card">Ответ пока не найден.</div>';
  const differs=normalize(row.original_question)!==normalize(row.normalized_question);
  return `<div class="answer-card">
    ${differs?`<div class="normalized"><strong>Нормализованная тема:</strong> ${esc(row.normalized_question)}</div>`:''}
    <p>${esc(ans.short_answer)}</p>
    <div class="source-section">Учебник: #${String(row.book_order).padStart(3,'0')} ${esc(row.book_section_title)}</div>
    ${readerLinks(topic)}
  </div>`;
}

function renderTicketGrid(){
  $('ticketGrid').innerHTML=Array.from({length:30},(_,i)=>i+1).map(n=>`<button class="ticket-button" data-ticket="${n}">№ ${n}</button>`).join('');
  $('ticketGrid').addEventListener('click',e=>{
    const b=e.target.closest('[data-ticket]'); if(!b)return;
    openTicket(Number(b.dataset.ticket));
  });
}

function openTicket(n){
  selectedTicket=n; ticketAnswersVisible=false;
  document.querySelectorAll('.ticket-button').forEach(b=>b.classList.toggle('active',Number(b.dataset.ticket)===n));
  renderTicket();
  $('ticketPanel').scrollIntoView({behavior:'smooth',block:'start'});
}

function renderTicket(){
  const rows=tickets.filter(x=>x.ticket===selectedTicket).sort((a,b)=>a.ticket_position-b.ticket_position);
  $('ticketPanel').innerHTML=`<article class="panel">
    <div class="panel-head"><div><div class="eyebrow">Зачёт с оценкой</div><h3>Билет № ${selectedTicket}</h3></div></div>
    <ol class="question-list">${rows.map(r=>`<li><span class="question-text">${esc(r.original_question)}</span>${ticketAnswersVisible?answerBlock(r):''}</li>`).join('')}</ol>
    <div class="controls">
      <button id="toggleTicketAnswers" class="action">${ticketAnswersVisible?'Скрыть ответы':'Показать ответы'}</button>
    </div>
  </article>`;
  $('toggleTicketAnswers').addEventListener('click',()=>{ticketAnswersVisible=!ticketAnswersVisible;renderTicket()});
}

function renderBook(){
  const grouped=[]; let current=null;
  for(const t of [...topics].sort((a,b)=>a.topic_order-b.topic_order)){
    if(!current||current.chapter!==t.chapter){current={chapter:t.chapter,items:[]};grouped.push(current)}
    current.items.push(t);
  }
  $('bookTopics').innerHTML=grouped.map(g=>`<section class="chapter-block">
    <h3 class="chapter-title">${esc(g.chapter||'Раздел учебника')}</h3>
    ${g.items.map(t=>{
      const a=answersByTopic.get(t.topic_id);
      return `<details class="topic-card">
        <summary><span class="topic-number">${t.topic_order}</span><span class="topic-summary-text">${esc(t.normalized_question)}</span></summary>
        <div class="topic-body">
          <p>${esc(a?.short_answer||'Ответ пока не найден.')}</p>
          <div class="ticket-refs"><strong>Билеты:</strong> ${esc(ticketRefs(t))}</div>
          <div class="source-section">Учебник: #${String(t.book_order).padStart(3,'0')} ${esc(t.book_section_title)}</div>
          ${readerLinks(t)}
        </div>
      </details>`
    }).join('')}
  </section>`).join('');
}

function topicSearchDocument(t){
  const a=answersByTopic.get(t.topic_id);
  const originals=(t.ticket_refs||[]).map(r=>r.original_question).join(' ');
  const refs=(t.ticket_refs||[]).map(r=>`билет ${r.ticket} вопрос ${r.position} ${r.ticket}.${r.position}`).join(' ');
  return normalize([t.normalized_question,t.book_section_title,t.chapter,originals,refs,a?.short_answer||''].join(' '));
}

function scoreTopic(t,query){
  const q=normalize(query); if(!q)return 0;
  const doc=topicSearchDocument(t);
  let score=doc.includes(q)?120:0;
  const qTokens=q.split(' ').filter(x=>x.length>1);
  const dWords=[...new Set(doc.split(' ').filter(Boolean))];
  let matched=0;
  for(const qt of qTokens){
    const qs=tokenStem(qt); let best=0;
    for(const dw of dWords){
      if(dw===qt){best=20;break}
      const ds=tokenStem(dw);
      if(ds===qs){best=Math.max(best,14);continue}
      if((dw.startsWith(qt)||qt.startsWith(dw)||ds.startsWith(qs)||qs.startsWith(ds))&&Math.min(qt.length,dw.length)>=4)best=Math.max(best,9);
      if(qt.length>=5&&dw.length>=5&&distance(qt,dw,1)<=1)best=Math.max(best,6);
    }
    if(best){matched++;score+=best}
  }
  if(qTokens.length>1&&matched<Math.ceil(qTokens.length*.5))return 0;
  return score;
}

function renderSearch(){
  const raw=$('searchInput').value.trim();
  if(!raw){$('searchMeta').textContent='';$('searchResults').innerHTML='<div class="notice">Введите одно или несколько ключевых слов.</div>';return}
  const found=topics.map(t=>({t,score:scoreTopic(t,raw)})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score||a.t.topic_order-b.t.topic_order).slice(0,50);
  $('searchMeta').textContent=found.length?`Найдено: ${found.length}${found.length===50?' (показаны первые 50)':''}`:'Совпадений не найдено.';
  $('searchResults').innerHTML=found.map(({t})=>{
    const a=answersByTopic.get(t.topic_id);
    return `<article class="search-result">
      <div class="eyebrow">По учебнику № ${t.topic_order} · билеты ${esc(ticketRefs(t))}</div>
      <h3>${esc(t.normalized_question)}</h3>
      <p>${esc(a?.short_answer||'')}</p>
      <div class="source-section">Учебник: #${String(t.book_order).padStart(3,'0')} ${esc(t.book_section_title)}</div>
      ${readerLinks(t)}
    </article>`;
  }).join('')||'';
}

async function init(){
  try{
    [tickets,topics,answers]=await Promise.all([
      fetch('data/ticket-questions.json').then(r=>{if(!r.ok)throw new Error('tickets');return r.json()}),
      fetch('data/topics.json').then(r=>{if(!r.ok)throw new Error('topics');return r.json()}),
      fetch('data/answers.json').then(r=>{if(!r.ok)throw new Error('answers');return r.json()})
    ]);
    if(tickets.length!==180||topics.length!==171||answers.length!==171)throw new Error('Неполный набор данных');
    answersByTopic=new Map(answers.map(x=>[x.topic_id,x]));
    topicsById=new Map(topics.map(x=>[x.topic_id,x]));
    renderTicketGrid(); renderBook();
    $('loading').classList.add('hidden');
    document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
    $('searchInput').addEventListener('input',renderSearch);
    const initial=['tickets','book','search'].includes(location.hash.slice(1))?location.hash.slice(1):'tickets';
    showView(initial);
  }catch(err){
    $('loading').textContent='Не удалось загрузить данные сайта. Откройте страницу через веб-сервер или GitHub Pages.';
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded',init);
