#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'source/tickets-original.txt'
BOOK=ROOT/'data/book-index.json'

M={
'01.1':3,'01.2':33,'01.3':83,'01.4':121,'01.5':170,'01.6':212,
'02.1':213,'02.2':122,'02.3':171,'02.4':5,'02.5':47,'02.6':84,
'03.1':6,'03.2':47,'03.3':124,'03.4':172,'03.5':213,'03.6':86,
'04.1':6,'04.2':31,'04.3':87,'04.4':125,'04.5':173,'04.6':213,
'05.1':7,'05.2':21,'05.3':71,'05.4':135,'05.5':213,'05.6':177,
'06.1':219,'06.2':174,'06.3':213,'06.4':169,'06.5':120,'06.6':71,
'07.1':8,'07.2':48,'07.3':67,'07.4':121,'07.5':183,'07.6':213,
'08.1':9,'08.2':24,'08.3':90,'08.4':137,'08.5':180,'08.6':213,
'09.1':219,'09.2':210,'09.3':168,'09.4':119,'09.5':81,'09.6':20,
'10.1':10,'10.2':95,'10.3':167,'10.4':182,'10.5':221,'10.6':70,
'11.1':20,'11.2':71,'11.3':183,'11.4':165,'11.5':223,'11.6':67,
'12.1':23,'12.2':69,'12.3':67,'12.4':164,'12.5':184,'12.6':224,
'13.1':24,'13.2':54,'13.3':93,'13.4':163,'13.5':186,'13.6':218,
'14.1':17,'14.2':71,'14.3':190,'14.4':220,'14.5':71,'14.6':161,
'15.1':13,'15.2':72,'15.3':97,'15.4':217,'15.5':189,'15.6':160,
'16.1':14,'16.2':78,'16.3':98,'16.4':191,'16.5':159,'16.6':216,
'17.1':15,'17.2':79,'17.3':99,'17.4':157,'17.5':193,'17.6':215,
'18.1':16,'18.2':80,'18.3':101,'18.4':194,'18.5':213,'18.6':156,
'19.1':18,'19.2':195,'19.3':236,'19.4':139,'19.5':102,'19.6':160,
'20.1':105,'20.2':240,'20.3':197,'20.4':36,'20.5':54,'20.6':155,
'21.1':25,'21.2':22,'21.3':198,'21.4':157,'21.5':238,'21.6':107,
'22.1':38,'22.2':22,'22.3':108,'22.4':152,'22.5':199,'22.6':237,
'23.1':27,'23.2':54,'23.3':110,'23.4':201,'23.5':235,'23.6':149,
'24.1':111,'24.2':151,'24.3':202,'24.4':234,'24.5':39,'24.6':49,
'25.1':40,'25.2':21,'25.3':152,'25.4':112,'25.5':203,'25.6':232,
'26.1':41,'26.2':53,'26.3':204,'26.4':231,'26.5':144,'26.6':117,
'27.1':42,'27.2':62,'27.3':113,'27.4':205,'27.5':233,'27.6':142,
'28.1':27,'28.2':50,'28.3':114,'28.4':141,'28.5':206,'28.6':236,
'29.1':43,'29.2':60,'29.3':115,'29.4':208,'29.5':234,'29.6':140,
'30.1':16,'30.2':209,'30.3':21,'30.4':116,'30.5':139,'30.6':241,
}

SECONDARY={
'02.5':[20],'03.2':[34],'07.3':[72,84],'07.5':[178],'09.5':[82],
'12.3':[72,84],'19.4':[],'21.2':[139],'23.2':[22,64],'26.1':[29],
'27.1':[30],'28.1':[38],'29.1':[38,43],
}

CONFIDENCE={k:'medium' for k in ['04.4','07.3','07.5','10.1','11.1','12.3','19.4','21.3','23.1','24.5','25.2','28.1','29.1']}
NOTES={
'04.4':'В исходнике отсутствует название конкретного чинопоследования; по структуре билета и ближайшему разделу учебника привязано к истории чина Елеосвящения.',
'07.3':'Формулировка объединяет происхождение и содержание исповеди; основной раздел — история формирования Покаяния, дополнительно указаны богословский смысл и история русской практики.',
'07.5':'Исходная формулировка смешивает выражение «схема чина по Требнику» с темой отпевания мирских человек; основная привязка дана к современной схеме отпевания мирян, дополнительная — к схеме «последования по исходе души».',
'10.1':'Формулировка почти дословно совпадает с общим разделом о видах священнодействий, но в билете добавлены слова «Таинства Крещения».',
'11.1':'Исходная формулировка грамматически повреждена; привязка дана к чину Крещения.',
'12.3':'В учебнике история и богословское содержание исповеди разнесены по нескольким разделам; указаны основной и дополнительные разделы.',
'19.4':'Отдельного заголовка «Символика Таинства причастия» в оглавлении нет; привязано к разделу «Таинство святой Евхаристии».',
'21.3':'В исходнике, вероятно, пропущено слово «отпевания»; привязано к схеме отпевания священников.',
'23.1':'История оглашения раскрывается внутри исторического блока чинопоследования Крещения; привязано к соответствующему разделу «Чин оглашения».',
'24.5':'Термин «предогласительная молитва» в оглавлении не выделен; по содержанию привязано к молитве «во еже сотворити оглашенного».',
'25.2':'Сугубая ектения и отпуст указаны в схеме Миропомазания, завершающей соединённое крещально-миропомазательное богослужение.',
'28.1':'История оглашения в Русской Церкви раскрывается в историческом разделе «Чин оглашения»; дополнительная ссылка ведёт к богословскому описанию чинопоследования.',
'29.1':'Отдельного одноимённого заголовка в оглавлении нет; молитва о призвании к Просвещению соотнесена с завершением оглашения и общим чинопоследованием.',
}

ORDER_CHILDREN={
17:[18,19,20,21,22],67:[68,69,70],72:[73,74,75,76,77,78,79,80,81,82,83],
87:[88,89],90:[91,92],93:[94,95],102:[103,104],
105:[106,107,108,109,110,111,112,113,114],170:[171,172,173,174],
204:[205,206],224:[225,226,227,228,229,230],
}

SUBSTANTIVE_NORMALIZATION={
'04.4':'История формирования чинопоследования',
'07.1':'«Последование молебных пений»',
'11.1':'Богослужение Таинства Крещения',
'21.3':'Схема чинопоследования отпевания священников',
'24.5':'Молитва предогласительная',
'28.5':'Схема чинопоследования над усопшим неправославным',
}

REPLACEMENTS=[
('Православиючерез','Православию через'),('Елеосвященияв','Елеосвящения в'),
('Последованиемолебных','Последование молебных'),('втробрачных','второбрачных'),
('формированиичинопоследования','формирования чинопоследования'),('чипа','чина'),
('Руссокой','Русской'),('чинопоследоваиия','чинопоследования'),
('внегдародити','внегда родити'),('архиреев','архиереев'),
('чинопоследованиянеправославным','чинопоследования неправославным'),
('в Крещения','в Крещении'),('о умершем','об умершем'),('проследования','последования'),
]

def parse_tickets():
    text=SRC.read_text(encoding='utf-8-sig')
    lines=[re.sub(r'\s+',' ',x.strip()) for x in text.splitlines()]
    rows=[]; ticket=None
    for line in lines:
        if not line or re.fullmatch(r'\d{1,3}',line): continue
        m=re.match(r'^Билет\s*№\s*(\d+)\s*$',line,re.I)
        if m:
            ticket=int(m.group(1)); continue
        m=re.match(r'^(\d+)\.\s*(.*)$',line)
        if m and ticket:
            rows.append({'ticket':ticket,'ticket_position':int(m.group(1)),'original_question':m.group(2).strip()})
        elif rows:
            rows[-1]['original_question'] += ' '+line
    return rows

def normalize_question(s,key):
    s=re.sub(r'\s+',' ',s).strip().rstrip(' »“”')
    for a,b in REPLACEMENTS: s=s.replace(a,b)
    s=re.sub(r'\s+([,.])',r'\1',s)
    s=re.sub(r'\s+',' ',s).strip()
    return SUBSTANTIVE_NORMALIZATION.get(key,s)

book=json.loads(BOOK.read_text(encoding='utf-8'))
by_order={x['order']:x for x in book}
rows=parse_tickets()
assert len(rows)==180
assert set(M)=={f"{r['ticket']:02d}.{r['ticket_position']}" for r in rows}

occ=[]
for r in rows:
    key=f"{r['ticket']:02d}.{r['ticket_position']}"
    order=M[key]; sec=by_order[order]
    refs=[]
    for o in [order]+SECONDARY.get(key,[])+ORDER_CHILDREN.get(order,[]):
        s=by_order[o]
        refs.append({'book_order':o,'section_title':s['title'],'chapter':s['chapter'],'epub_href':s['href'],'reader_href':f"reader.html?href={s['href']}"})
    nq=normalize_question(r['original_question'],key)
    topic_key=nq.lower().replace('ё','е')+'|'+str(order)
    topic_id='topic-'+hashlib.sha1(topic_key.encode('utf-8')).hexdigest()[:10]
    occ.append({
        'id':f"T{r['ticket']:02d}Q{r['ticket_position']}",
        'ticket':r['ticket'],'ticket_position':r['ticket_position'],
        'original_question':r['original_question'],'normalized_question':nq,
        'topic_id':topic_id,'book_order':order,'chapter':sec['chapter'],
        'book_section_title':sec['title'],'epub_href':sec['href'],
        'reader_href':f"reader.html?href={sec['href']}",'book_refs':refs,
        'mapping_confidence':CONFIDENCE.get(key,'high'),'mapping_note':NOTES.get(key,''),
    })

ordered=sorted(occ,key=lambda x:(x['book_order'],x['normalized_question'].lower(),x['ticket'],x['ticket_position']))
for i,r in enumerate(ordered,1): r['study_order']=i
study_order_by_id={r['id']:r['study_order'] for r in ordered}
for r in occ: r['study_order']=study_order_by_id[r['id']]

groups={}
for r in occ:
    g=groups.setdefault(r['topic_id'],{
        'topic_id':r['topic_id'],'normalized_question':r['normalized_question'],
        'book_order':r['book_order'],'chapter':r['chapter'],'book_section_title':r['book_section_title'],
        'epub_href':r['epub_href'],'reader_href':r['reader_href'],'book_refs':r['book_refs'],
        'mapping_confidence':r['mapping_confidence'],'mapping_notes':[], 'ticket_refs':[]})
    g['ticket_refs'].append({'ticket':r['ticket'],'position':r['ticket_position'],'id':r['id'],'original_question':r['original_question']})
    if r['mapping_note'] and r['mapping_note'] not in g['mapping_notes']: g['mapping_notes'].append(r['mapping_note'])

topics=sorted(groups.values(),key=lambda x:(x['book_order'],x['normalized_question'].lower()))
for i,t in enumerate(topics,1): t['topic_order']=i

(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'docs').mkdir(exist_ok=True)
(ROOT/'data/ticket-questions.json').write_text(json.dumps(occ,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/questions-by-book.json').write_text(json.dumps(ordered,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'data/topics.json').write_text(json.dumps(topics,ensure_ascii=False,indent=2),encoding='utf-8')

with (ROOT/'docs/QUESTION-REGISTER.md').open('w',encoding='utf-8') as f:
    f.write('# Нормализованный реестр экзаменационных вопросов\n\n')
    f.write(f'- Экзаменационных позиций: **{len(occ)}**.\n')
    f.write(f'- Нормализованных тем: **{len(topics)}**.\n')
    f.write('- Исходная формулировка всегда сохраняется отдельно и не заменяется нормализованной.\n\n')
    f.write('| № по учебнику | Билет | № | Исходный вопрос | Нормализованный вопрос | Раздел учебника | EPUB | Уверенность |\n')
    f.write('|---:|---:|---:|---|---|---|---|---|\n')
    for r in ordered:
        oq=r['original_question'].replace('|','\\|'); nq=r['normalized_question'].replace('|','\\|'); st=r['book_section_title'].replace('|','\\|')
        f.write(f"| {r['study_order']} | {r['ticket']} | {r['ticket_position']} | {oq} | {nq} | #{r['book_order']:03d} {st} | \`{r['epub_href']}\` | {r['mapping_confidence']} |\n")

with (ROOT/'docs/MAPPING-REVIEW.md').open('w',encoding='utf-8') as f:
    f.write('# Сопоставления, требующие особого внимания\n\n')
    for r in ordered:
        if r['mapping_confidence']!='high':
            f.write(f"## {r['id']} — {r['original_question']}\n\n")
            f.write(f"- Нормализовано: **{r['normalized_question']}**\n")
            f.write(f"- Основной раздел: **#{r['book_order']:03d} {r['book_section_title']}** (\`{r['epub_href']}\`)\n")
            if len(r['book_refs'])>1:
                f.write('- Дополнительные разделы: '+', '.join(f"#{x['book_order']:03d} {x['section_title']}" for x in r['book_refs'][1:])+'\n')
            f.write(f"- Основание/примечание: {r['mapping_note']}\n\n")

print('occurrences',len(occ),'topics',len(topics),'review',sum(1 for r in occ if r['mapping_confidence']!='high'))
