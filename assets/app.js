'use strict';

var tickets=[];
var topics=[];
var answers=[];
var answersByTopic=new Map();
var topicsById=new Map();
var selectedTicket=null;
var ticketAnswersVisible=false;

var $=function(id){return document.getElementById(id);};
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c];});};

function normalize(s){
  return String(s==null?'':s).toLowerCase().replace(/ё/g,'е').replace(/[^а-яa-z0-9]+/gi,' ').replace(/\s+/g,' ').trim();
}

function tokenStem(w){
  var suffixes=['иями','ями','ами','ение','ения','ений','ание','ания','аний','ского','скому','скими','ская','ское','ские','остью','ости','ов','ев','ами','ями','ого','ему','ами','ах','ях','ый','ий','ая','ое','ые','ую','юю','ом','ем','ам','ям','а','я','ы','и','у','ю','е'];
  if(w.length<5)return w;
  for(var i=0;i<suffixes.length;i++){
    var s=suffixes[i];
    if(w.length-s.length>=4&&w.endsWith(s))return w.slice(0,-s.length);
  }
  return w;
}

function distance(a,b,max){
  max=max||2;
  if(Math.abs(a.length-b.length)>max)return max+1;
  var prev=Array.from({length:b.length+1},function(_,i){return i;});
  for(var i=1;i<=a.length;i++){
    var cur=[i],rowMin=i;
    for(var j=1;j<=b.length;j++){
      cur[j]=Math.min(cur[j-1]+1,prev[j]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
      rowMin=Math.min(rowMin,cur[j]);
    }
    if(rowMin>max)return max+1;
    for(var k=0;k<cur.length;k++)prev[k]=cur[k];
  }
  return prev[b.length];
}

function replaceUrl(params){
  var q=params.toString();
  history.replaceState(null,'',q?'?'+q:location.pathname.split('/').pop());
}

function showView(name,updateUrl){
  if(updateUrl===undefined)updateUrl=true;
  document.querySelectorAll('.view').forEach(function(x){x.classList.add('hidden');});
  $(name+'View').classList.remove('hidden');
  document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('active',x.dataset.view===name);});
  if(updateUrl){
    var p=new URLSearchParams();
    p.set('view',name);
    replaceUrl(p);
  }
  if(name==='search')setTimeout(function(){$('searchInput').focus();},0);
}

function ticketRefs(topic){
  return (topic.ticket_refs||[]).map(function(r){return '№'+r.ticket+'.'+r.position;}).join(', ');
}

function contextToken(ctx){
  if(ctx.view==='tickets')return 'ticket:'+ctx.ticket+':'+ctx.position;
  if(ctx.view==='search')return 'search';
  return 'book';
}

function returnTarget(ctx){
  var p=new URLSearchParams();
  p.set('view',ctx.view||'tickets');
  if(ctx.view==='tickets'){
    p.set('ticket',String(ctx.ticket));
    p.set('answers','1');
    p.set('focus',ctx.focus||'');
  }else if(ctx.view==='book'){
    p.set('topic',ctx.topic||'');
  }else if(ctx.view==='search'){
    p.set('q',ctx.query||'');
    p.set('topic',ctx.topic||'');
  }
  return 'index.html?'+p.toString();
}

function readerHref(obj,ctx){
  var p=new URLSearchParams();
  p.set('href',obj.epub_href);
  p.set('topic',obj.topic_id);
  p.set('return',returnTarget(ctx));
  p.set('ctx',contextToken(ctx));
  return 'reader.html?'+p.toString();
}

function readerButton(obj,ctx){
  return '<div class="reader-links"><a class="reader-link" href="'+esc(readerHref(obj,ctx))+'">Подробнее в учебнике</a></div>';
}

function answerBlock(row){
  var ans=answersByTopic.get(row.topic_id);
  var topic=topicsById.get(row.topic_id)||row;
  if(!ans)return '<div class="answer-card">Ответ пока не найден.</div>';
  var differs=normalize(row.original_question)!==normalize(row.normalized_question);
  var html='<div class="answer-card">';
  if(differs)html+='<div class="normalized"><strong>Нормализованная тема:</strong> '+esc(row.normalized_question)+'</div>';
  html+='<p>'+esc(ans.short_answer)+'</p>';
  html+='<div class="source-section">Учебник: #'+String(row.book_order).padStart(3,'0')+' '+esc(row.book_section_title)+'</div>';
  html+=readerButton(topic,{view:'tickets',ticket:row.ticket,position:row.ticket_position,focus:row.id});
  html+='</div>';
  return html;
}

function renderTicketGrid(){
  $('ticketGrid').innerHTML=Array.from({length:30},function(_,i){return i+1;}).map(function(n){
    return '<button class="ticket-button" data-ticket="'+n+'">№ '+n+'</button>';
  }).join('');
  $('ticketGrid').addEventListener('click',function(e){
    var b=e.target.closest('[data-ticket]');
    if(!b)return;
    openTicket(Number(b.dataset.ticket),{update:true,answers:false});
  });
}

function updateTicketUrl(){
  var p=new URLSearchParams();
  p.set('view','tickets');
  if(selectedTicket)p.set('ticket',String(selectedTicket));
  if(ticketAnswersVisible)p.set('answers','1');
  replaceUrl(p);
}

function openTicket(n,opts){
  opts=opts||{};
  selectedTicket=n;
  ticketAnswersVisible=!!opts.answers;
  document.querySelectorAll('.ticket-button').forEach(function(b){b.classList.toggle('active',Number(b.dataset.ticket)===n);});
  renderTicket();
  if(opts.update!==false)updateTicketUrl();
  if(opts.focus){
    setTimeout(function(){focusReturnedElement('question-'+opts.focus);},40);
  }else if(opts.scroll!==false){
    $('ticketPanel').scrollIntoView({behavior:'smooth',block:'start'});
  }
}

function renderTicket(){
  var rows=tickets.filter(function(x){return x.ticket===selectedTicket;}).sort(function(a,b){return a.ticket_position-b.ticket_position;});
  var items=rows.map(function(r){
    return '<li id="question-'+esc(r.id)+'"><span class="question-text">'+esc(r.original_question)+'</span>'+(ticketAnswersVisible?answerBlock(r):'')+'</li>';
  }).join('');
  $('ticketPanel').innerHTML='<article class="panel">'+
    '<div class="panel-head"><div><div class="eyebrow">Зачёт с оценкой</div><h3>Билет № '+selectedTicket+'</h3></div></div>'+
    '<ol class="question-list">'+items+'</ol>'+
    '<div class="controls"><button id="toggleTicketAnswers" class="action">'+(ticketAnswersVisible?'Скрыть ответы':'Показать ответы')+'</button></div>'+
    '</article>';
  $('toggleTicketAnswers').addEventListener('click',function(){
    ticketAnswersVisible=!ticketAnswersVisible;
    renderTicket();
    updateTicketUrl();
  });
}

function renderBook(){
  var grouped=[],current=null;
  topics.slice().sort(function(a,b){return a.topic_order-b.topic_order;}).forEach(function(t){
    if(!current||current.chapter!==t.chapter){
      current={chapter:t.chapter,items:[]};
      grouped.push(current);
    }
    current.items.push(t);
  });
  $('bookTopics').innerHTML=grouped.map(function(g){
    var cards=g.items.map(function(t){
      var a=answersByTopic.get(t.topic_id);
      return '<details class="topic-card" id="topic-'+esc(t.topic_id)+'" data-topic="'+esc(t.topic_id)+'">'+
        '<summary><span class="topic-number">'+t.topic_order+'</span><span class="topic-summary-text">'+esc(t.normalized_question)+'</span></summary>'+
        '<div class="topic-body">'+
          '<p>'+esc(a?a.short_answer:'Ответ пока не найден.')+'</p>'+
          '<div class="ticket-refs"><strong>Билеты:</strong> '+esc(ticketRefs(t))+'</div>'+
          '<div class="source-section">Учебник: #'+String(t.book_order).padStart(3,'0')+' '+esc(t.book_section_title)+'</div>'+
          readerButton(t,{view:'book',topic:t.topic_id})+
        '</div>'+
      '</details>';
    }).join('');
    return '<section class="chapter-block"><h3 class="chapter-title">'+esc(g.chapter||'Раздел учебника')+'</h3>'+cards+'</section>';
  }).join('');
}

function topicSearchDocument(t){
  var a=answersByTopic.get(t.topic_id);
  var originals=(t.ticket_refs||[]).map(function(r){return r.original_question;}).join(' ');
  var refs=(t.ticket_refs||[]).map(function(r){return 'билет '+r.ticket+' вопрос '+r.position+' '+r.ticket+'.'+r.position;}).join(' ');
  return normalize([t.normalized_question,t.book_section_title,t.chapter,originals,refs,a?a.short_answer:''].join(' '));
}

function scoreTopic(t,query){
  var q=normalize(query);
  if(!q)return 0;
  var doc=topicSearchDocument(t);
  var score=doc.includes(q)?120:0;
  var qTokens=q.split(' ').filter(function(x){return x.length>1;});
  var dWords=Array.from(new Set(doc.split(' ').filter(Boolean)));
  var matched=0;
  qTokens.forEach(function(qt){
    var qs=tokenStem(qt),best=0;
    for(var i=0;i<dWords.length;i++){
      var dw=dWords[i];
      if(dw===qt){best=20;break;}
      var ds=tokenStem(dw);
      if(ds===qs){best=Math.max(best,14);continue;}
      if((dw.startsWith(qt)||qt.startsWith(dw)||ds.startsWith(qs)||qs.startsWith(ds))&&Math.min(qt.length,dw.length)>=4)best=Math.max(best,9);
      if(qt.length>=5&&dw.length>=5&&distance(qt,dw,1)<=1)best=Math.max(best,6);
    }
    if(best){matched++;score+=best;}
  });
  if(qTokens.length>1&&matched<Math.ceil(qTokens.length*.5))return 0;
  return score;
}

function updateSearchUrl(){
  var p=new URLSearchParams();
  p.set('view','search');
  var raw=$('searchInput').value.trim();
  if(raw)p.set('q',raw);
  replaceUrl(p);
}

function renderSearch(updateUrl){
  if(updateUrl===undefined)updateUrl=true;
  var raw=$('searchInput').value.trim();
  if(updateUrl)updateSearchUrl();
  if(!raw){
    $('searchMeta').textContent='';
    $('searchResults').innerHTML='<div class="notice">Введите одно или несколько ключевых слов.</div>';
    return;
  }
  var found=topics.map(function(t){return {t:t,score:scoreTopic(t,raw)};})
    .filter(function(x){return x.score>0;})
    .sort(function(a,b){return b.score-a.score||a.t.topic_order-b.t.topic_order;})
    .slice(0,50);
  $('searchMeta').textContent=found.length?'Найдено: '+found.length+(found.length===50?' (показаны первые 50)':''):'Совпадений не найдено.';
  $('searchResults').innerHTML=found.map(function(item){
    var t=item.t,a=answersByTopic.get(t.topic_id);
    return '<article class="search-result" id="search-'+esc(t.topic_id)+'">'+
      '<div class="eyebrow">По учебнику № '+t.topic_order+' · билеты '+esc(ticketRefs(t))+'</div>'+
      '<h3>'+esc(t.normalized_question)+'</h3>'+
      '<p>'+esc(a?a.short_answer:'')+'</p>'+
      '<div class="source-section">Учебник: #'+String(t.book_order).padStart(3,'0')+' '+esc(t.book_section_title)+'</div>'+
      readerButton(t,{view:'search',query:raw,topic:t.topic_id})+
    '</article>';
  }).join('');
}

function focusReturnedElement(id){
  var el=document.getElementById(id);
  if(!el)return;
  if(el.tagName==='DETAILS')el.open=true;
  el.classList.add('return-focus');
  el.scrollIntoView({behavior:'smooth',block:'center'});
  setTimeout(function(){el.classList.remove('return-focus');},2400);
}

function restoreInitialState(){
  var p=new URLSearchParams(location.search);
  var view=p.get('view');
  if(['tickets','book','search'].indexOf(view)<0)view='tickets';
  showView(view,false);

  if(view==='tickets'){
    var n=parseInt(p.get('ticket')||'',10);
    if(n>=1&&n<=30){
      openTicket(n,{
        update:false,
        answers:p.get('answers')==='1',
        focus:p.get('focus')||'',
        scroll:!p.get('focus')
      });
    }
  }else if(view==='book'){
    var topic=p.get('topic');
    if(topic)setTimeout(function(){focusReturnedElement('topic-'+topic);},40);
  }else if(view==='search'){
    var q=p.get('q')||'';
    $('searchInput').value=q;
    renderSearch(false);
    var searchTopic=p.get('topic');
    if(searchTopic)setTimeout(function(){focusReturnedElement('search-'+searchTopic);},40);
  }
}

async function init(){
  try{
    var loaded=await Promise.all([
      fetch('data/ticket-questions.json').then(function(r){if(!r.ok)throw new Error('tickets');return r.json();}),
      fetch('data/topics.json').then(function(r){if(!r.ok)throw new Error('topics');return r.json();}),
      fetch('data/answers.json').then(function(r){if(!r.ok)throw new Error('answers');return r.json();})
    ]);
    tickets=loaded[0];topics=loaded[1];answers=loaded[2];
    if(tickets.length!==180||topics.length!==171||answers.length!==171)throw new Error('Неполный набор данных');
    answersByTopic=new Map(answers.map(function(x){return [x.topic_id,x];}));
    topicsById=new Map(topics.map(function(x){return [x.topic_id,x];}));
    renderTicketGrid();
    renderBook();
    $('loading').classList.add('hidden');
    document.querySelectorAll('.tab').forEach(function(b){
      b.addEventListener('click',function(){showView(b.dataset.view,true);});
    });
    $('searchInput').addEventListener('input',function(){renderSearch(true);});
    restoreInitialState();
  }catch(err){
    $('loading').textContent='Не удалось загрузить данные сайта. Откройте страницу через веб-сервер или GitHub Pages.';
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded',init);
