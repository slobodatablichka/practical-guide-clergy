#!/usr/bin/env python3
import json,re,zipfile
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
EPUB=ROOT/'assets/book/taintstva-i-obryady-pravoslavnoy-tserkvi.epub'
TOPICS=ROOT/'data/topics.json'
OUT=ROOT/'data/answers.json'

STOP=set('и в на по о об от до к ко с со из за для при во что это как а но или их его ее её им ими над под через быть был была были есть который которая которые которых где когда также уже еще ещё не'.split())

MANUAL_ANSWERS={
    'Периоды в истории богослужений Русской Церкви': (
        'Богослужебная жизнь Русской Церкви делится на три периода. '
        'Первый — до конца XIV века: господство Студийского устава, введённого в русскую практику преподобным Феодосием Печерским. '
        'Второй — конец XIV–XV века: распространение Иерусалимского устава, переведённого на славянский язык преподобным Афанасием Высотским; к концу XIV — началу XV века он получает повсеместное признание. '
        'Третий — с начала XVI века: развитие местных уставов при господстве Иерусалимского устава.'
    ),
    'Молитвы ребенку, предваряющие Крещение': (
        'К молитвам младенцу, предваряющим Крещение, учебник относит наречение имени и 3-ю и 4-ю молитвы сорокового дня. '
        'В целом предкрещальные молитвословия связаны с посвящением младенца Богу и подготовкой к его духовному рождению в Таинстве Крещения.'
    ),
    'Завершение исповеди': (
        'После исповедания грехов духовник даёт «Завещание» — наставление не повторять исповеданные грехи. '
        'Затем читается молитва над преклонённой главой и тайносовершительная молитва «Господь и Бог наш, Иисус Христос…». '
        'После «Достойно есть…» совершается отпуст; исповедь завершается увещанием духовного отца. '
        'Целование Евангелия и Креста выражает примирение с Господом и решимость исправить жизнь.'
    ),
    'Тайносовершительный момент Крещения': (
        'Тайносовершительный момент Крещения — троекратное погружение крещаемого в воду единого тайнодействия. '
        'Погружение означает приобщение к смерти Христа, а выход из воды — новое, благодатное рождение и вступление в жизнь Церкви.'
    ),
    'Введение во храм': (
        'При воцерковлении младенца вводят в храм со словами «Воцерковляется…». '
        'Этот обряд выражает посвящение младенца Богу и его видимое сопричисление к Церкви; внесение в алтарь указывает, что для духовной жизни необходимы силы, даруемые Церковью в Таинствах и богослужении.'
    ),
    'Причащение Святых Христовых Таин': (
        'Воцерковление завершается причащением младенца Тела и Крови Христовых. '
        'По объяснению учебника, это видимый знак его «сочетания Христу» и Его Церкви и начало постоянного участия нового члена Церкви в евхаристической жизни.'
    ),
}

def norm(s):
    s=s.lower().replace('ё','е')
    s=re.sub(r'[^а-я0-9]+',' ',s)
    return ' '.join(s.split())

def stems(s):
    out=[]
    for w in norm(s).split():
        if w in STOP or len(w)<4: continue
        out.append(w[:6])
    return set(out)

def clean_block(s):
    s=' '.join(s.replace('\xa0',' ').split())
    s=re.sub(r'(?<=\D)\s+\d{1,3}(?=\s|$)',' ',s)
    return s.strip()

def clip(s,n=1000):
    s=' '.join(s.split())
    if len(s)<=n: return s
    cut=s[:n]
    p=max(cut.rfind('. '),cut.rfind('; '),cut.rfind(', '))
    if p>n*0.65: cut=cut[:p+1]
    return cut.rstrip(' ,;:')+'…'

def blocks_for(z,href,title):
    soup=BeautifulSoup(z.read(href.split('#')[0]),'html.parser')
    blocks=[]
    for tag in soup.body.find_all(['div','p','li'],recursive=False):
        txt=clean_block(' '.join(tag.stripped_strings))
        if not txt: continue
        if norm(txt)==norm(title): continue
        if txt=='Таинства и обряды Православной Церкви': continue
        blocks.append(txt)
    if not blocks:
        txt=clean_block(' '.join(soup.stripped_strings))
        prefix='Таинства и обряды Православной Церкви '+title
        if txt.startswith(prefix): txt=txt[len(prefix):].strip()
        blocks=[txt] if txt else []
    return [b for b in blocks if b.strip()]

def sentence_chunks(blocks):
    chunks=[]
    for b in blocks:
        if len(b)<180:
            chunks.append(b); continue
        parts=re.split(r'(?<=[.!?])\s+(?=[А-ЯЁ«])',b)
        chunks.extend([p.strip() for p in parts if p.strip()])
    return chunks

def answer_for(topic,blocks):
    q=topic['normalized_question']; qn=norm(q); qst=stems(q)
    schema=('схем' in qn or ('чинопоследован' in qn and not any(x in qn for x in ['истори','происхожд','содержан'])))
    history=any(x in qn for x in ['истори','возникнов','происхожд','формирован','установлен'])
    meaning=any(x in qn for x in ['символ','смысл','богослов','назначен','обоснован'])

    if topic['book_order']==213:
        text=' '.join(blocks)
        if 'мясопуст' in qn or 'вселенск' in qn or 'троиц' in qn:
            m=re.search(r'Вселенские родительские субботы(.{0,2200})',text,re.I)
            if m: return clip('Вселенские родительские субботы.'+m.group(1),1100)
        if '2 й' in qn or 'седмиц' in qn or 'четыредесят' in qn:
            for phrase in ['Родительские субботы Великого поста','субботы 2-й, 3-й и 4-й']:
                i=norm(text).find(norm(phrase))
                if i>=0: return clip(text[i:i+1700],1100)
        if 'новопрестав' in qn:
            for phrase in ['3-й, 9-й, 40-й день','3-й, 9-й, 40-й']:
                i=text.find(phrase)
                if i>=0: return clip(text[i:i+1500],1050)
        if 'поминальн' in qn or 'родительск' in qn:
            i=text.find('Вселенские родительские субботы')
            if i>=0: return clip(text[i:i+2100],1100)

    if schema:
        selected=[]
        for b in blocks:
            if len(selected)>=18: break
            if len(b)>260 and selected: break
            selected.append(b)
        return clip(' → '.join(selected),1200)

    chunks=sentence_chunks(blocks)
    if not chunks: return ''
    if history: return clip(' '.join(chunks[:5]),1050)

    scored=[]
    for idx,c in enumerate(chunks):
        st=stems(c); ov=len(qst & st)
        scored.append(((ov if meaning else ov*3) - idx*(0.015 if meaning else 0.02),idx,c))
    chosen=[chunks[0]]
    for _,idx,c in sorted(scored,reverse=True):
        if c not in chosen: chosen.append(c)
        if len(chosen)>=4: break
    chosen.sort(key=lambda c:chunks.index(c))
    return clip(' '.join(chosen),1000 if meaning else 950)

topics=json.loads(TOPICS.read_text(encoding='utf-8'))
answers=[]
with zipfile.ZipFile(EPUB) as z:
    for t in topics:
        blocks=blocks_for(z,t['epub_href'],t['book_section_title'])
        if not blocks and len(t.get('book_refs',[]))>1:
            child_blocks=[]
            for ref in t['book_refs'][1:]:
                cb=blocks_for(z,ref['epub_href'],ref['section_title'])
                if cb: child_blocks.extend(cb)
                elif ref['section_title']: child_blocks.append(ref['section_title'])
            blocks=child_blocks
        ans=MANUAL_ANSWERS.get(t['normalized_question']) or answer_for(t,blocks)
        answers.append({
            'topic_id':t['topic_id'],'topic_order':t['topic_order'],
            'question':t['normalized_question'],'short_answer':ans,
            'source_book_order':t['book_order'],'source_section_title':t['book_section_title'],
            'epub_href':t['epub_href'],'reader_href':t['reader_href'],
            'answer_method':'source-grounded extractive draft',
        })
OUT.write_text(json.dumps(answers,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Built {len(answers)} source-grounded short answers.')
