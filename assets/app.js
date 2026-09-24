'use strict';

var tickets=[];
var topics=[];
var textbooks=[];
var textbookById=new Map();
var topicsById=new Map();
var answersByBook=new Map();

var selectedTicket=null;
var openTicketAnswer=null;
var selectedBookView='nefedov';
var openSearchAnswer=null;

var feedbackClient=null;
var feedbackByKey=new Map();
var FEEDBACK_NAME_KEY='practical-guide-clergy:feedback-name';
var SUPABASE_URL='https://chlffvzahnntudukloer.supabase.co';
var SUPABASE_PUBLISHABLE_KEY='sb_publishable_KYJLtO7PeBh94w3gCVnV4Q_KSwM1sqS';

var $=function(id){return document.getElementById(id);};
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c];});};

function normalize(s){
  return String(s==null?'':s).toLowerCase().replace(/ё/g,'е').replace(/[^а-яa-z0-9]+/gi,' ').replace(/\s+/g,' ').trim();
}

function tokenStem(w){
  var suffixes=['иями','ями','ами','ение','ения','ений','ание','ания','аний','ского','скому','скими','ская','ское','ские','остью','ости','ов','ев','ого','ему','ому','ах','ях','ый','ий','ая','ое','ые','ую','юю','ом','ем','ам','ям','а','я','ы','и','у','ю','е'];
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

function validBook(id){
  return textbookById.has(id);
}

function answerFor(bookId,topicId){
  var map=answersByBook.get(bookId);
  return map?map.get(topicId):null;
}

function fullnessLabel(rel){
  var labels={
    5:'полный ответ',
    4:'почти полный',
    3:'частичный ответ',
    2:'отдельные сведения',
    1:'прямого ответа нет'
  };
  return labels[Number(rel)]||'полнота не определена';
}

function fullnessScale(rel){
  var n=Math.max(1,Math.min(5,Number(rel)||1));
  return '<span class="fullness-scale" aria-hidden="true"><span class="fullness-filled">'+
    '■'.repeat(n)+'</span><span class="fullness-empty">'+'□'.repeat(5-n)+'</span></span>'+
    '<span class="sr-only">Полнота: '+esc(fullnessLabel(n))+'</span>';
}

function bookSurname(book){
  var author=String(book&&book.author||'').trim().replace(/[.,]+$/,'');
  if(!author)return book&&book.short_label?book.short_label:'Учебник';
  var parts=author.split(/\s+/);
  return parts[parts.length-1];
}

function bookTooltip(book,rel){
  return book.author+', «'+book.title+'». Полнота материала по вопросу: '+fullnessLabel(rel)+'.';
}

function feedbackKey(topicId,bookId){
  return topicId+'|'+bookId;
}

function getFeedbackName(){
  try{return (localStorage.getItem(FEEDBACK_NAME_KEY)||'').trim();}catch(e){return '';}
}

function storeFeedbackName(name){
  name=String(name||'').trim().slice(0,100);
  if(!name)return '';
  try{localStorage.setItem(FEEDBACK_NAME_KEY,name);}catch(e){}
  return name;
}

function clearFeedbackName(){
  try{localStorage.removeItem(FEEDBACK_NAME_KEY);}catch(e){}
}

function feedbackNameAreaHtml(name){
  if(name){
    return '<div class="feedback-name-saved">Имя: <strong>'+esc(name)+'</strong> <button type="button" class="feedback-link" data-feedback-change-name>Сменить</button></div>';
  }
  return '<label class="feedback-field feedback-name-field"><span>Ваше имя</span><input type="text" maxlength="100" autocomplete="name" placeholder="Имя или псевдоним" data-feedback-name></label>';
}

function feedbackInnerHtml(topicId,bookId){
  var existing=feedbackByKey.get(feedbackKey(topicId,bookId))||null;
  var selected=existing?Number(existing.rating):0;
  var comment=existing&&existing.comment?existing.comment:'';
  var name=getFeedbackName();
  var buttons=[1,2,3,4,5].map(function(n){
    return '<button type="button" class="feedback-rating-button'+(selected===n?' active':'')+'" data-feedback-rating="'+n+'" aria-label="Оценка '+n+' из 5" aria-pressed="'+(selected===n?'true':'false')+'">'+n+'</button>';
  }).join('');
  return '<div class="feedback-title">Оценить ответ</div>'+
    '<div class="feedback-grid">'+
      '<div class="feedback-name-area">'+feedbackNameAreaHtml(name)+'</div>'+
      '<div class="feedback-field feedback-rating-field"><span>Оценка 1–5</span><div class="feedback-rating-buttons">'+buttons+'</div></div>'+
      '<label class="feedback-field feedback-comment-field"><span>Комментарий <small>необязательно</small></span><textarea rows="2" maxlength="2000" placeholder="Замечание к ответу" data-feedback-comment>'+esc(comment)+'</textarea></label>'+
    '</div>'+
    '<div class="feedback-status'+(existing?' saved':'')+'" aria-live="polite">'+(existing?'Сохранено':'')+'</div>';
}

function feedbackBlock(topicId,bookId,ctx){
  ctx=ctx||{};
  return '<div class="feedback-box" data-feedback-topic="'+esc(topicId)+'" data-feedback-book="'+esc(bookId)+'" data-feedback-view="'+esc(ctx.view||'book')+'"'+
    (ctx.questionId?' data-feedback-question-id="'+esc(ctx.questionId)+'"':'')+
    (ctx.ticket?' data-feedback-ticket="'+esc(ctx.ticket)+'"':'')+
    (ctx.position?' data-feedback-position="'+esc(ctx.position)+'"':'')+
    '>'+feedbackInnerHtml(topicId,bookId)+'</div>';
}

function syncFeedbackNameAreas(name){
  document.querySelectorAll('.feedback-name-area').forEach(function(area){
    area.innerHTML=feedbackNameAreaHtml(name);
  });
}

function setFeedbackStatus(block,message,kind){
  var el=block&&block.querySelector('.feedback-status');
  if(!el)return;
  el.textContent=message||'';
  el.classList.toggle('error',kind==='error');
  el.classList.toggle('saved',kind==='saved');
}

function refreshFeedbackBlock(block){
  if(!block)return;
  var topicId=block.dataset.feedbackTopic;
  var bookId=block.dataset.feedbackBook;
  block.innerHTML=feedbackInnerHtml(topicId,bookId);
}

function refreshFeedbackBlocks(){
  document.querySelectorAll('.feedback-box').forEach(function(block){
    if(block.contains(document.activeElement))return;
    refreshFeedbackBlock(block);
  });
}

async function answerRevision(answer){
  var text=[answer&&answer.short_answer||'',answer&&answer.book_section_title||'',answer&&answer.relevance||''].join('\n');
  try{
    if(window.crypto&&window.crypto.subtle&&window.TextEncoder){
      var digest=await window.crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
      return Array.from(new Uint8Array(digest)).map(function(b){return b.toString(16).padStart(2,'0');}).join('');
    }
  }catch(e){}
  var h=2166136261;
  for(var i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,16777619);}
  return 'fnv1a-'+(h>>>0).toString(16).padStart(8,'0');
}

function feedbackContext(block){
  var topicId=block.dataset.feedbackTopic;
  var bookId=block.dataset.feedbackBook;
  var view=block.dataset.feedbackView||'book';
  var topic=topicsById.get(topicId);
  var answer=answerFor(bookId,topicId);
  var question=topic?topic.normalized_question:'';
  var ticket=null,position=null;
  if(view==='tickets'){
    var qid=block.dataset.feedbackQuestionId||'';
    var row=tickets.find(function(x){return x.id===qid;});
    if(row){
      question=row.original_question;
      ticket=row.ticket;
      position=row.ticket_position;
    }
  }
  return {topicId:topicId,bookId:bookId,view:view,topic:topic,answer:answer,question:question,ticket:ticket,position:position};
}

function initFeedbackClient(){
  try{
    if(window.supabase&&typeof window.supabase.createClient==='function'){
      feedbackClient=window.supabase.createClient(SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY,{
        auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
      });
    }
  }catch(err){
    console.error('Feedback client initialization failed',err);
    feedbackClient=null;
  }
}

async function loadOwnFeedback(){
  if(!feedbackClient)return;
  var sessionResult=await feedbackClient.auth.getSession();
  var session=sessionResult&&sessionResult.data?sessionResult.data.session:null;
  if(!session)return;
  var result=await feedbackClient.from('answer_feedback')
    .select('topic_id,book_id,display_name,rating,comment,answer_revision,updated_at');
  if(result.error)throw result.error;
  (result.data||[]).forEach(function(row){
    feedbackByKey.set(feedbackKey(row.topic_id,row.book_id),row);
  });
  if(!getFeedbackName()&&result.data&&result.data.length){
    storeFeedbackName(result.data[0].display_name);
  }
}

async function ensureFeedbackSession(){
  if(!feedbackClient)throw new Error('feedback-client-unavailable');
  var current=await feedbackClient.auth.getSession();
  if(current.data&&current.data.session)return current.data.session;
  var created=await feedbackClient.auth.signInAnonymously();
  if(created.error)throw created.error;
  return created.data.session;
}

async function saveFeedback(block,ratingOverride){
  if(!block)return;
  var active=block.querySelector('.feedback-rating-button.active');
  var rating=Number(ratingOverride||(active&&active.dataset.feedbackRating)||0);
  if(!rating){
    setFeedbackStatus(block,'Сначала выберите оценку.','error');
    return;
  }

  var name=getFeedbackName();
  var nameInput=block.querySelector('[data-feedback-name]');
  if(!name&&nameInput)name=String(nameInput.value||'').trim();
  if(!name){
    setFeedbackStatus(block,'Сначала укажите имя.','error');
    if(nameInput)nameInput.focus();
    return;
  }
  name=storeFeedbackName(name);
  syncFeedbackNameAreas(name);

  var ctx=feedbackContext(block);
  if(!ctx.answer||!ctx.topic){
    setFeedbackStatus(block,'Не удалось определить оцениваемый ответ.','error');
    return;
  }
  var commentInput=block.querySelector('[data-feedback-comment]');
  var comment=commentInput?String(commentInput.value||'').trim():'';

  setFeedbackStatus(block,'Сохраняю…','');
  try{
    var session=await ensureFeedbackSession();
    var revision=await answerRevision(ctx.answer);
    var payload={
      user_id:session.user.id,
      display_name:name,
      topic_id:ctx.topicId,
      book_id:ctx.bookId,
      question:ctx.question,
      source_rel:Number(ctx.answer.relevance)||1,
      rating:rating,
      comment:comment||null,
      answer_revision:revision,
      view:ctx.view,
      ticket:ctx.ticket,
      position:ctx.position
    };
    var result=await feedbackClient.from('answer_feedback')
      .upsert(payload,{onConflict:'user_id,topic_id,book_id'})
      .select('topic_id,book_id,display_name,rating,comment,answer_revision,updated_at')
      .single();
    if(result.error)throw result.error;
    feedbackByKey.set(feedbackKey(ctx.topicId,ctx.bookId),result.data);
    refreshFeedbackBlock(block);
    setFeedbackStatus(block,'Сохранено','saved');
  }catch(err){
    console.error('Feedback save failed',err);
    setFeedbackStatus(block,'Не удалось сохранить. Попробуйте ещё раз.','error');
  }
}

function bindFeedbackEvents(){
  document.addEventListener('click',function(e){
    var change=e.target.closest('[data-feedback-change-name]');
    if(change){
      var changeBlock=change.closest('.feedback-box');
      clearFeedbackName();
      syncFeedbackNameAreas('');
      var input=changeBlock&&changeBlock.querySelector('[data-feedback-name]');
      if(input)input.focus();
      return;
    }

    var ratingButton=e.target.closest('[data-feedback-rating]');
    if(!ratingButton)return;
    var block=ratingButton.closest('.feedback-box');
    if(!block)return;
    block.querySelectorAll('[data-feedback-rating]').forEach(function(btn){
      var active=btn===ratingButton;
      btn.classList.toggle('active',active);
      btn.setAttribute('aria-pressed',active?'true':'false');
    });
    saveFeedback(block,Number(ratingButton.dataset.feedbackRating));
  });

  document.addEventListener('change',function(e){
    if(e.target.matches('[data-feedback-name]')){
      var name=storeFeedbackName(e.target.value);
      if(name)syncFeedbackNameAreas(name);
      return;
    }
    if(e.target.matches('[data-feedback-comment]')){
      var block=e.target.closest('.feedback-box');
      var active=block&&block.querySelector('.feedback-rating-button.active');
      if(active)saveFeedback(block,Number(active.dataset.feedbackRating));
      else if(block)setFeedbackStatus(block,'Комментарий сохранится после выбора оценки.','');
    }
  });
}


function showView(name,updateUrl){
  if(updateUrl===undefined)updateUrl=true;
  document.querySelectorAll('.view').forEach(function(x){x.classList.add('hidden');});
  $(name+'View').classList.remove('hidden');
  document.querySelectorAll('.tab').forEach(function(x){x.classList.toggle('active',x.dataset.view===name);});
  if(updateUrl){
    var p=new URLSearchParams();
    p.set('view',name);
    if(name==='book')p.set('book',selectedBookView);
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

function returnTarget(ctx,bookId){
  var p=new URLSearchParams();
  p.set('view',ctx.view||'tickets');
  if(ctx.view==='tickets'){
    p.set('ticket',String(ctx.ticket));
    p.set('focus',ctx.focus||'');
    p.set('source',bookId);
  }else if(ctx.view==='book'){
    p.set('book',bookId);
    p.set('topic',ctx.topic||'');
  }else if(ctx.view==='search'){
    p.set('q',ctx.query||'');
    p.set('topic',ctx.topic||'');
    p.set('source',bookId);
  }
  return 'index.html?'+p.toString();
}

function readerHref(answer,ctx,bookId){
  var p=new URLSearchParams();
  p.set('book',bookId);
  p.set('href',answer.epub_href);
  p.set('topic',answer.topic_id);
  p.set('return',returnTarget(ctx,bookId));
  p.set('ctx',contextToken(ctx));
  return 'reader.html?'+p.toString();
}

function readerButton(answer,ctx,bookId){
  if(!answer||!answer.epub_href)return '';
  return '<div class="reader-links"><a class="reader-link" href="'+esc(readerHref(answer,ctx,bookId))+'">Подробнее в учебнике</a></div>';
}

function sourceButtons(topicId,activeBookId,mode,questionId){
  return '<div class="source-choice-row">'+textbooks.map(function(book){
    var ans=answerFor(book.id,topicId);
    var rel=ans?ans.relevance:1;
    var active=activeBookId===book.id;
    var attr=mode==='ticket'
      ? ' data-ticket-source="'+esc(book.id)+'" data-question-id="'+esc(questionId)+'"'
      : ' data-search-source="'+esc(book.id)+'" data-topic-id="'+esc(topicId)+'"';
    var surname=bookSurname(book);
    var tip=bookTooltip(book,rel);
    return '<button class="source-choice'+(active?' active':'')+'" type="button"'+attr+
      ' title="'+esc(tip)+'" aria-label="'+esc(surname+'. Полнота: '+fullnessLabel(rel)+'. '+tip)+'">'+
      '<span class="source-surname">'+esc(surname)+'</span> '+fullnessScale(rel)+'</button>';
  }).join('')+'</div>';
}

function answerBlockForTicket(row,bookId){
  var ans=answerFor(bookId,row.topic_id);
  var book=textbookById.get(bookId);
  if(!ans||!book)return '';
  var differs=normalize(row.original_question)!==normalize(row.normalized_question);
  var html='<div class="answer-card">';
  if(differs)html+='<div class="normalized"><strong>Нормализованная тема:</strong> '+esc(row.normalized_question)+'</div>';
  html+='<p>'+esc(ans.short_answer)+'</p>';
  if(ans.epub_href){
    html+=readerButton(ans,{view:'tickets',ticket:row.ticket,position:row.ticket_position,focus:row.id},bookId);
  }else{
    html+='<div class="source-section">Прямой раздел в этом учебнике не найден.</div>';
  }
  html+=feedbackBlock(row.topic_id,bookId,{view:'tickets',questionId:row.id,ticket:row.ticket,position:row.ticket_position});
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
    openTicket(Number(b.dataset.ticket),{update:true});
  });
}

function updateTicketUrl(){
  var p=new URLSearchParams();
  p.set('view','tickets');
  if(selectedTicket)p.set('ticket',String(selectedTicket));
  if(openTicketAnswer){
    p.set('focus',openTicketAnswer.questionId);
    p.set('source',openTicketAnswer.bookId);
  }
  replaceUrl(p);
}

function openTicket(n,opts){
  opts=opts||{};
  selectedTicket=n;
  openTicketAnswer=null;
  if(opts.focus&&opts.source&&validBook(opts.source)){
    var exists=tickets.some(function(x){return x.ticket===n&&x.id===opts.focus;});
    if(exists)openTicketAnswer={questionId:opts.focus,bookId:opts.source};
  }
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
    var active=openTicketAnswer&&openTicketAnswer.questionId===r.id?openTicketAnswer.bookId:null;
    return '<li id="question-'+esc(r.id)+'">'+
      '<span class="question-text">'+esc(r.original_question)+'</span>'+
      sourceButtons(r.topic_id,active,'ticket',r.id)+
      (active?answerBlockForTicket(r,active):'')+
    '</li>';
  }).join('');
  $('ticketPanel').innerHTML='<article class="panel">'+
    '<div class="panel-head"><div><h3>Билет № '+selectedTicket+'</h3></div></div>'+
    '<ol class="question-list">'+items+'</ol>'+
    '</article>';
}

function renderBookSourceTabs(){
  $('bookSourceTabs').innerHTML=textbooks.map(function(book){
    return '<button type="button" class="source-tab'+(book.id===selectedBookView?' active':'')+'" data-book-view="'+esc(book.id)+'" '+
      'title="'+esc(book.author+', «'+book.title+'»')+'">'+esc(bookSurname(book))+'</button>';
  }).join('');
}

function updateBookUrl(topicId){
  var p=new URLSearchParams();
  p.set('view','book');
  p.set('book',selectedBookView);
  if(topicId)p.set('topic',topicId);
  replaceUrl(p);
}

function setBookView(bookId,updateUrl){
  if(!validBook(bookId))bookId=textbooks[0].id;
  selectedBookView=bookId;
  renderBookSourceTabs();
  renderBook();
  if(updateUrl!==false)updateBookUrl('');
}

function renderBook(){
  var rows=topics.map(function(t){
    return {topic:t,answer:answerFor(selectedBookView,t.topic_id)};
  }).sort(function(a,b){
    var ao=a.answer&&a.answer.book_order!=null?a.answer.book_order:Number.MAX_SAFE_INTEGER;
    var bo=b.answer&&b.answer.book_order!=null?b.answer.book_order:Number.MAX_SAFE_INTEGER;
    return ao-bo||a.topic.topic_order-b.topic.topic_order;
  });

  var grouped=[],current=null;
  rows.forEach(function(row){
    var chapter=(row.answer&&row.answer.chapter)||'Прямого материала в учебнике не найдено';
    if(!current||current.chapter!==chapter){
      current={chapter:chapter,items:[]};
      grouped.push(current);
    }
    current.items.push(row);
  });

  $('bookTopics').innerHTML=grouped.map(function(g){
    var cards=g.items.map(function(row){
      var t=row.topic,a=row.answer;
      var rel=a?a.relevance:1;
      var source='';
      if(a&&a.epub_href){
        source=readerButton(a,{view:'book',topic:t.topic_id},selectedBookView);
      }else{
        source='<div class="source-section">Прямой раздел в этом учебнике не найден.</div>';
      }
      return '<details class="topic-card" id="topic-'+esc(selectedBookView)+'-'+esc(t.topic_id)+'" data-topic="'+esc(t.topic_id)+'">'+
        '<summary><span class="topic-number">'+t.topic_order+'</span><span class="topic-summary-text">'+esc(t.normalized_question)+'</span><span class="rel-badge" title="'+esc('Полнота материала: '+fullnessLabel(rel))+'">'+fullnessScale(rel)+'</span></summary>'+
        '<div class="topic-body">'+
          '<p>'+esc(a?a.short_answer:'Ответ пока не найден.')+'</p>'+
          '<div class="ticket-refs"><strong>Билеты:</strong> '+esc(ticketRefs(t))+'</div>'+
          source+
          feedbackBlock(t.topic_id,selectedBookView,{view:'book'})+
        '</div>'+
      '</details>';
    }).join('');
    return '<section class="chapter-block"><h3 class="chapter-title">'+esc(g.chapter)+'</h3>'+cards+'</section>';
  }).join('');
}

function topicSearchDocument(t){
  var originals=(t.ticket_refs||[]).map(function(r){return r.original_question;}).join(' ');
  var refs=(t.ticket_refs||[]).map(function(r){return 'билет '+r.ticket+' вопрос '+r.position+' '+r.ticket+'.'+r.position;}).join(' ');
  var sources=textbooks.map(function(book){
    var a=answerFor(book.id,t.topic_id);
    return a?[a.short_answer,a.book_section_title,a.chapter].join(' '):'';
  }).join(' ');
  return normalize([t.normalized_question,originals,refs,sources].join(' '));
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
  if(openSearchAnswer){
    p.set('topic',openSearchAnswer.topicId);
    p.set('source',openSearchAnswer.bookId);
  }
  replaceUrl(p);
}

function searchAnswerBlock(t,bookId,query){
  var a=answerFor(bookId,t.topic_id);
  var book=textbookById.get(bookId);
  if(!a||!book)return '';
  var html='<div class="answer-card search-answer-card">';
  html+='<p>'+esc(a.short_answer)+'</p>';
  if(a.epub_href){
    html+=readerButton(a,{view:'search',query:query,topic:t.topic_id},bookId);
  }else{
    html+='<div class="source-section">Прямой раздел в этом учебнике не найден.</div>';
  }
  html+=feedbackBlock(t.topic_id,bookId,{view:'search'});
  html+='</div>';
  return html;
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
    var t=item.t;
    var active=openSearchAnswer&&openSearchAnswer.topicId===t.topic_id?openSearchAnswer.bookId:null;
    return '<article class="search-result" id="search-'+esc(t.topic_id)+'">'+
      '<div class="eyebrow">Билеты '+esc(ticketRefs(t))+'</div>'+
      '<h3>'+esc(t.normalized_question)+'</h3>'+
      sourceButtons(t.topic_id,active,'search','')+
      (active?searchAnswerBlock(t,active,raw):'')+
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

  if(view==='book'){
    var requestedBook=p.get('book');
    if(validBook(requestedBook))selectedBookView=requestedBook;
    renderBookSourceTabs();
    renderBook();
  }

  showView(view,false);

  if(view==='tickets'){
    var n=parseInt(p.get('ticket')||'',10);
    if(n>=1&&n<=30){
      openTicket(n,{
        update:false,
        source:p.get('source')||'',
        focus:p.get('focus')||'',
        scroll:!p.get('focus')
      });
    }
  }else if(view==='book'){
    var topic=p.get('topic');
    if(topic)setTimeout(function(){focusReturnedElement('topic-'+selectedBookView+'-'+topic);},40);
  }else if(view==='search'){
    var q=p.get('q')||'';
    var searchTopic=p.get('topic')||'';
    var source=p.get('source')||'';
    if(searchTopic&&validBook(source))openSearchAnswer={topicId:searchTopic,bookId:source};
    $('searchInput').value=q;
    renderSearch(false);
    if(searchTopic)setTimeout(function(){focusReturnedElement('search-'+searchTopic);},40);
  }
}

async function init(){
  try{
    initFeedbackClient();
    bindFeedbackEvents();
    var base=await Promise.all([
      fetch('data/ticket-questions.json').then(function(r){if(!r.ok)throw new Error('tickets');return r.json();}),
      fetch('data/topics.json').then(function(r){if(!r.ok)throw new Error('topics');return r.json();}),
      fetch('data/textbooks.json').then(function(r){if(!r.ok)throw new Error('textbooks');return r.json();})
    ]);
    tickets=base[0];topics=base[1];textbooks=base[2];
    if(tickets.length!==180||topics.length!==171||textbooks.length<2)throw new Error('Неполный набор данных');

    textbookById=new Map(textbooks.map(function(x){return [x.id,x];}));
    if(!validBook(selectedBookView))selectedBookView=textbooks[0].id;

    var answerSets=await Promise.all(textbooks.map(function(book){
      return fetch(book.answers_path).then(function(r){if(!r.ok)throw new Error(book.id);return r.json();});
    }));
    textbooks.forEach(function(book,i){
      var rows=answerSets[i];
      if(rows.length!==171)throw new Error('Неполный набор ответов '+book.id);
      answersByBook.set(book.id,new Map(rows.map(function(x){return [x.topic_id,x];})));
    });
    topicsById=new Map(topics.map(function(x){return [x.topic_id,x];}));

    renderTicketGrid();
    renderBookSourceTabs();
    renderBook();

    $('ticketPanel').addEventListener('click',function(e){
      var b=e.target.closest('[data-ticket-source]');
      if(!b)return;
      var questionId=b.dataset.questionId;
      var bookId=b.dataset.ticketSource;
      if(openTicketAnswer&&openTicketAnswer.questionId===questionId&&openTicketAnswer.bookId===bookId){
        openTicketAnswer=null;
      }else{
        openTicketAnswer={questionId:questionId,bookId:bookId};
      }
      renderTicket();
      updateTicketUrl();
      setTimeout(function(){var el=$('question-'+questionId);if(el)el.scrollIntoView({block:'nearest'});},0);
    });

    $('bookSourceTabs').addEventListener('click',function(e){
      var b=e.target.closest('[data-book-view]');
      if(!b)return;
      setBookView(b.dataset.bookView,true);
    });

    $('searchResults').addEventListener('click',function(e){
      var b=e.target.closest('[data-search-source]');
      if(!b)return;
      var topicId=b.dataset.topicId;
      var bookId=b.dataset.searchSource;
      if(openSearchAnswer&&openSearchAnswer.topicId===topicId&&openSearchAnswer.bookId===bookId){
        openSearchAnswer=null;
      }else{
        openSearchAnswer={topicId:topicId,bookId:bookId};
      }
      renderSearch(true);
      setTimeout(function(){var el=$('search-'+topicId);if(el)el.scrollIntoView({block:'nearest'});},0);
    });

    $('loading').classList.add('hidden');
    document.querySelectorAll('.tab').forEach(function(b){
      b.addEventListener('click',function(){showView(b.dataset.view,true);});
    });
    $('searchInput').addEventListener('input',function(){
      openSearchAnswer=null;
      renderSearch(true);
    });
    restoreInitialState();
    loadOwnFeedback().then(function(){refreshFeedbackBlocks();}).catch(function(err){
      console.error('Feedback load failed',err);
    });
  }catch(err){
    $('loading').textContent='Не удалось загрузить данные сайта. Откройте страницу через веб-сервер или GitHub Pages.';
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded',init);
