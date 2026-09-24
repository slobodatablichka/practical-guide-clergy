#!/usr/bin/env python3
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TOPICS_PATH = ROOT / 'data/topics.json'
LEGACY_ANSWERS_PATH = ROOT / 'data/answers.json'
LEGACY_INDEX_PATH = ROOT / 'data/book-index.json'
OUT_ROOT = ROOT / 'data/textbooks'

BOOKS = [
    {
        'id': 'nefedov',
        'number': 1,
        'short_label': 'Уч.1',
        'author': 'протоиерей Геннадий Нефёдов',
        'title': 'Таинства и обряды Православной Церкви',
        'epub_path': 'assets/book/taintstva-i-obryady-pravoslavnoy-tserkvi.epub',
        'index_path': 'data/textbooks/nefedov/book-index.json',
        'answers_path': 'data/textbooks/nefedov/answers.json',
    },
    {
        'id': 'silchenkov',
        'number': 2,
        'short_label': 'Уч.2',
        'author': 'протоиерей Николай Сильченков',
        'title': 'Практическое руководство при совершении приходских треб',
        'epub_path': 'assets/book/silchenkov-prakticheskoe-rukovodstvo-pri-sovershenii-prikhodskikh-treb.epub',
        'index_path': 'data/textbooks/silchenkov/book-index.json',
        'answers_path': 'data/textbooks/silchenkov/answers.json',
    },
]

STOP = set('''
и в во на по о об от до к ко с со из за для при что это как а но или их его ее её им ими над под через
быть был была были есть который которая которые которых где когда также уже еще ещё не оный сей эта эти
весь вся все всея между после перед подле согласно согласно же ли либо
'''.split())

GENERIC = set('''
схема чин чинопоследование чинопоследования последование последования богослужение богослужения
совершение совершения порядок история исторический происхождение содержание идейный смысл значение
молитва молитвы молитвословие молитвословий таинство таинства обряд обряды церковь церкви русский русской
правило правила церковный церковные вопрос вопросы
'''.split())

SUFFIXES = [
    'иями','ями','ами','ение','ения','ений','ание','ания','аний','ского','скому','скими','ская','ское',
    'ские','остью','ости','овать','ывает','ывает','ение','ения','ого','ему','ому','ами','ями','ах','ях',
    'ый','ий','ая','ое','ые','ую','юю','ом','ем','ам','ям','ов','ев','а','я','ы','и','у','ю','е'
]

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def norm(value):
    value = str(value or '').lower().replace('ё', 'е')
    value = re.sub(r'[^а-яa-z0-9]+', ' ', value)
    return ' '.join(value.split())

def stem_word(word):
    if len(word) < 5:
        return word
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word

def terms(value, keep_generic=False):
    out = set()
    for word in norm(value).split():
        if len(word) < 4 or word in STOP:
            continue
        if not keep_generic and word in GENERIC:
            continue
        out.add(stem_word(word))
    return out

def overlap(query_terms, source_terms):
    if not query_terms:
        return 0.0
    return len(query_terms & source_terms) / len(query_terms)

def clean_title(value):
    return re.sub(r'^\s*\d+[.)]?\s*', '', str(value or '')).strip()

def source_body(item):
    text = str(item.get('text') or '')
    title = str(item.get('title') or '')
    nt = norm(title)
    ntext = norm(text)
    if nt and ntext == nt:
        return ''
    if title and text.startswith(title):
        text = text[len(title):].strip()
    return text

def clip(value, limit=1050):
    value = ' '.join(str(value or '').split())
    if len(value) <= limit:
        return value
    cut = value[:limit]
    stop = max(cut.rfind('. '), cut.rfind('; '), cut.rfind(', '))
    if stop > limit * 0.65:
        cut = cut[:stop + 1]
    return cut.rstrip(' ,;:') + '…'

def clean_block(value):
    value = ' '.join(str(value or '').replace('\xa0', ' ').split())
    value = re.sub(r'(?<=\D)\s+\d{1,3}(?=\s|$)', ' ', value)
    return value.strip()

def sentence_chunks(blocks):
    chunks = []
    for block in blocks:
        if len(block) < 180:
            chunks.append(block)
        else:
            chunks.extend(
                part.strip()
                for part in re.split(r'(?<=[.!?])\s+(?=[А-ЯЁ«])', block)
                if part.strip()
            )
    return chunks

def blocks_for(zf, href, title):
    try:
        raw = zf.read(href.split('#')[0])
    except KeyError:
        return []
    soup = BeautifulSoup(raw, 'html.parser')
    body = soup.body or soup
    blocks = []
    for tag in body.find_all(['p', 'li', 'blockquote', 'div'], recursive=False):
        text = clean_block(' '.join(tag.stripped_strings))
        if not text or norm(text) == norm(title):
            continue
        blocks.append(text)
    if not blocks:
        text = clean_block(' '.join(body.stripped_strings))
        nt = norm(title)
        if nt and norm(text).startswith(nt):
            text = text[len(title):].strip()
        if text:
            blocks = [text]
    return blocks

def silchenkov_chapter(order):
    ranges = [
        (2, 2, 'Общие постановления'),
        (3, 18, 'Молитвы при рождении ребёнка и сорокового дня'),
        (19, 43, 'Крещение и Миропомазание'),
        (44, 66, 'Исповедь'),
        (67, 74, 'Причащение'),
        (75, 105, 'Брак'),
        (106, 112, 'Елеоосвящение'),
        (113, 142, 'Погребение и поминовение усопших'),
        (143, 148, 'Крестные ходы'),
        (149, 154, 'Водоосвящение'),
        (155, 169, 'Молебные пения'),
        (170, 178, 'Благословение дома, икон и предметов'),
        (179, 183, 'Присяга'),
        (184, 309, 'Служебный указатель'),
    ]
    for start, end, title in ranges:
        if start <= order <= end:
            return title
    return 'Практическое руководство'

def index_epub(epub_path, book_id):
    ns = {'n': 'http://www.daisy.org/z3986/2005/ncx/'}
    items = []
    with zipfile.ZipFile(epub_path) as zf:
        root = ET.fromstring(zf.read('toc.ncx'))

        def walk(node, depth=0):
            title_node = node.find('n:navLabel/n:text', ns)
            content_node = node.find('n:content', ns)
            if title_node is None or content_node is None:
                return
            title = (title_node.text or '').strip()
            href = content_node.attrib.get('src', '')
            order = int(node.attrib.get('playOrder', 0) or 0)
            try:
                raw = zf.read(href.split('#')[0])
                text = ' '.join(BeautifulSoup(raw, 'html.parser').stripped_strings)
            except Exception:
                text = ''
            pure_number = bool(re.fullmatch(r'\d+', title))
            chapter = silchenkov_chapter(order) if book_id == 'silchenkov' else None
            items.append({
                'order': order,
                'depth': depth,
                'title': title,
                'href': href,
                'chapter': chapter,
                'text': text,
                'usable': not pure_number,
            })
            for child in node.findall('n:navPoint', ns):
                walk(child, depth + 1)

        nav_map = root.find('n:navMap', ns)
        for node in nav_map.findall('n:navPoint', ns):
            walk(node)

    items.sort(key=lambda x: x['order'])
    return items

def silchenkov_range(question):
    q = norm(question)

    # Темы, которых этот учебник прямо не рассматривает.
    if any(x in q for x in ['хиротон', 'хиротес', 'таинство священства', 'возведение в чины']):
        return None
    if any(x in q for x in ['чин чтеца', 'чина чтеца', 'чин певца', 'чина певца']):
        return None
    if 'освящ' in q and 'храм' in q:
        return None
    if 'требник' in q and ('истор' in q or 'происхожд' in q):
        return None
    if 'период' in q and 'богослуж' in q:
        return None

    if any(x in q for x in ['родити', 'рожд', 'наречен имени', 'изверг', 'сороков', '40 го дня']):
        return (3, 18)
    if 'миропомаз' in q or 'присоедин' in q:
        return (34, 43)
    if any(x in q for x in ['крещ', 'оглаш', 'воцерков']):
        return (19, 43)
    if any(x in q for x in ['исповед', 'покаян', 'епитим']):
        return (44, 66)
    if any(x in q for x in ['причащ', 'евхарист']):
        return (67, 74)
    if any(x in q for x in ['брак', 'венчан', 'обручен', 'второбрач', 'родств', 'брач']):
        return (75, 105)
    if any(x in q for x in ['елеосвящ', 'соборован']):
        return (106, 112)
    if any(x in q for x in ['погреб', 'отпев', 'усопш', 'панихид', 'заупокой', 'помин', 'лития']):
        return (113, 142)
    if 'крестн' in q and 'ход' in q:
        return (143, 148)
    if 'водоосвящ' in q or ('освящ' in q and 'вод' in q):
        return (149, 154)
    if 'молеб' in q:
        return (155, 169)
    if any(x in q for x in ['нового дома', 'дом', 'икон', 'благословен предмет']):
        return (170, 178)
    if 'присяг' in q:
        return (179, 183)
    return (2, 183)

def facet_cap(question, title, text, relevance):
    q = norm(question)
    source = norm((title or '') + ' ' + (text or ''))
    if any(x in q for x in ['истор', 'возникнов', 'происхожд', 'формирован']):
        if not any(x in source for x in ['истор', 'древн', 'век', 'возник', 'происх', 'впервые', 'обычай']):
            relevance = min(relevance, 2)
    if any(x in q for x in ['символ', 'идейный смысл', 'богослов', 'значение']):
        if not any(x in source for x in ['означ', 'символ', 'смысл', 'образ', 'знак', 'выражает']):
            relevance = min(relevance, 3)
    return relevance

def relevance_score(question, title, text, confidence='high', unsupported=False):
    if unsupported:
        return 1
    qterms = terms(question)
    if not qterms:
        qterms = terms(question, keep_generic=True)
    if not qterms:
        return 1
    tterms = terms(title)
    xterms = terms(text)
    title_cov = overlap(qterms, tterms)
    body_cov = overlap(qterms, xterms)
    exact = norm(clean_title(title)) == norm(question)

    if exact or title_cov >= 0.75 or body_cov >= 0.90:
        rel = 5
    elif title_cov >= 0.50 or body_cov >= 0.70:
        rel = 4
    elif title_cov >= 0.25 or body_cov >= 0.50:
        rel = 3
    elif body_cov >= 0.25:
        rel = 2
    else:
        rel = 1

    rel = facet_cap(question, title, text, rel)
    if confidence == 'medium':
        rel = min(rel, 3)
    return max(1, min(5, rel))

def candidate_score(question, item):
    qterms = terms(question)
    if not qterms:
        qterms = terms(question, keep_generic=True)
    body = source_body(item)
    tterms = terms(item['title'])
    xterms = terms(body)
    title_cov = overlap(qterms, tterms)
    body_cov = overlap(qterms, xterms)
    score = title_cov * 7 + body_cov * 4

    q = norm(question)
    title = norm(item['title'])
    if q and (q in title or title in q):
        score += 2.5

    # Заголовки Сильченкова часто функциональные; связываем тип вопроса
    # с его собственными рубриками, не подменяя содержание.
    if any(x in q for x in ['схема', 'порядок', 'чинопослед']):
        if 'обрядовый порядок' in title or 'порядок' in title:
            score += 3.0
    if any(x in q for x in ['завершен', 'окончан', 'заключительн']):
        if 'заключительные действия' in title:
            score += 4.0
    if any(x in q for x in ['подготов', 'предварительн']):
        if 'подготовительные действия' in title:
            score += 3.0
    if 'тайносоверш' in q and 'обрядовый порядок' in title:
        score += 3.0
    if 'правил' in q and ('правил' in title or 'постановлен' in title):
        score += 2.0
    if 'время' in q and 'время' in title:
        score += 2.0
    if 'место' in q and 'место' in title:
        score += 2.0

    # Пустые рубричные страницы не должны выигрывать у содержащих текст
    # подразделов только за счёт совпадения названия.
    if len(norm(body)) < 40:
        score -= 5.0
    return score

def best_silchenkov_item(question, index):
    allowed = silchenkov_range(question)
    if allowed is None:
        return None, 0.0
    start, end = allowed
    candidates = [
        item for item in index
        if item.get('usable', True) and start <= item['order'] <= end
    ]
    if not candidates:
        return None, 0.0
    ranked = sorted(
        ((candidate_score(question, item), item) for item in candidates),
        key=lambda pair: (-pair[0], pair[1]['order'])
    )
    score, item = ranked[0]
    if score <= 0.20:
        return None, score
    return item, score

def extractive_answer(question, blocks, relevance):
    if relevance <= 1:
        return 'В учебнике прямого материала для ответа на этот вопрос не найдено.', []

    chunks = [x for x in sentence_chunks(blocks) if len(norm(x)) >= 20]
    if not chunks:
        return 'В выбранном разделе учебника прямой краткий ответ не выделяется.', []

    qterms = terms(question)
    if not qterms:
        qterms = terms(question, keep_generic=True)
    q = norm(question)
    schema = any(x in q for x in ['схема', 'порядок', 'чинопослед'])

    scored = []
    for idx, chunk in enumerate(chunks):
        cterms = terms(chunk)
        ov = len(qterms & cterms)
        score = ov * 5 - idx * 0.01
        if schema and any(x in norm(chunk) for x in ['затем', 'после', 'далее', 'сначала', 'священник']):
            score += 1
        scored.append((score, idx, chunk))

    chosen = []
    for score, idx, chunk in sorted(scored, reverse=True):
        if score <= 0 and chosen:
            continue
        if chunk not in chosen:
            chosen.append(chunk)
        if len(chosen) >= (5 if schema else 4):
            break

    if not chosen:
        chosen = chunks[:3]

    chosen.sort(key=lambda x: chunks.index(x))
    if schema:
        answer = ' → '.join(chosen)
    else:
        answer = ' '.join(chosen)

    fragments = [clip(x, 800) for x in chosen[:3] if len(norm(x)) >= 20]
    return clip(answer, 1100), fragments

topics = load(TOPICS_PATH)
legacy_answers = load(LEGACY_ANSWERS_PATH)
legacy_answers_by_id = {x['topic_id']: x for x in legacy_answers}
legacy_index = load(LEGACY_INDEX_PATH)
legacy_index_by_order = {x['order']: x for x in legacy_index}

# Реестр учебников.
dump(ROOT / 'data/textbooks.json', BOOKS)

# Учебник 1: сохраняем существующее ручное сопоставление и ответы,
# добавляя независимую оценку релевантности.
nefedov_dir = OUT_ROOT / 'nefedov'
nefedov_index = []
for item in legacy_index:
    copy = dict(item)
    copy['usable'] = True
    nefedov_index.append(copy)
dump(nefedov_dir / 'book-index.json', nefedov_index)

nefedov_answers = []
for topic in topics:
    old = legacy_answers_by_id[topic['topic_id']]
    item = legacy_index_by_order.get(topic['book_order'], {})
    rel = relevance_score(
        topic['normalized_question'],
        topic.get('book_section_title', ''),
        item.get('text', ''),
        topic.get('mapping_confidence', 'high'),
    )
    nefedov_answers.append({
        'book_id': 'nefedov',
        'topic_id': topic['topic_id'],
        'topic_order': topic['topic_order'],
        'question': topic['normalized_question'],
        'short_answer': old['short_answer'],
        'relevance': rel,
        'relevance_method': 'automatic_initial_v1',
        'mapping_confidence': topic.get('mapping_confidence', 'high'),
        'book_order': topic['book_order'],
        'chapter': topic.get('chapter'),
        'book_section_title': topic.get('book_section_title'),
        'epub_href': topic.get('epub_href'),
        'source_fragments': old.get('source_fragments', []),
        'answer_method': old.get('answer_method', 'source-grounded extractive draft'),
    })
dump(nefedov_dir / 'answers.json', nefedov_answers)

# Учебник 2: строим собственный индекс, первичное сопоставление и
# источник-ориентированные черновики ответов.
sil_book = next(x for x in BOOKS if x['id'] == 'silchenkov')
sil_epub = ROOT / sil_book['epub_path']
sil_index = index_epub(sil_epub, 'silchenkov')
dump(OUT_ROOT / 'silchenkov/book-index.json', sil_index)

sil_answers = []
with zipfile.ZipFile(sil_epub) as zf:
    for topic in topics:
        question = topic['normalized_question']
        item, score = best_silchenkov_item(question, sil_index)
        if item is None:
            sil_answers.append({
                'book_id': 'silchenkov',
                'topic_id': topic['topic_id'],
                'topic_order': topic['topic_order'],
                'question': question,
                'short_answer': 'В учебнике прямого материала для ответа на этот вопрос не найдено.',
                'relevance': 1,
                'relevance_method': 'automatic_initial_v1',
                'mapping_confidence': 'low',
                'mapping_score': round(score, 3),
                'book_order': None,
                'chapter': None,
                'book_section_title': None,
                'epub_href': None,
                'source_fragments': [],
                'answer_method': 'no direct source found',
            })
            continue

        rel = relevance_score(question, item['title'], source_body(item))
        blocks = blocks_for(zf, item['href'], item['title'])
        answer, fragments = extractive_answer(question, blocks, rel)
        # Если из выбранного EPUB-раздела нельзя извлечь ни одного
        # проверяемого фрагмента, не изображаем наличие источника.
        if rel >= 2 and not fragments:
            rel = 1
            answer = 'В учебнике прямого материала для ответа на этот вопрос не найдено.'
            fragments = []
        confidence = 'high' if rel >= 4 else ('medium' if rel == 3 else 'low')
        sil_answers.append({
            'book_id': 'silchenkov',
            'topic_id': topic['topic_id'],
            'topic_order': topic['topic_order'],
            'question': question,
            'short_answer': answer,
            'relevance': rel,
            'relevance_method': 'automatic_initial_v1',
            'mapping_confidence': confidence,
            'mapping_score': round(score, 3),
            'book_order': item['order'],
            'chapter': item['chapter'],
            'book_section_title': item['title'],
            'epub_href': item['href'],
            'source_fragments': fragments,
            'answer_method': 'source-grounded extractive draft',
        })
dump(OUT_ROOT / 'silchenkov/answers.json', sil_answers)

def distribution(rows):
    result = {str(i): 0 for i in range(1, 6)}
    for row in rows:
        result[str(row['relevance'])] += 1
    return result

status = {
    'method': 'automatic_initial_v1',
    'note': 'Оценки rel являются первичной автоматической оценкой релевантности материала учебника вопросу и подлежат последовательной ручной проверке.',
    'books': {
        'nefedov': {'answers': len(nefedov_answers), 'distribution': distribution(nefedov_answers)},
        'silchenkov': {'answers': len(sil_answers), 'distribution': distribution(sil_answers)},
    },
}
dump(ROOT / 'data/relevance-status.json', status)

print('Built multi-textbook data:')
print('  Nefedov:', len(nefedov_answers), distribution(nefedov_answers))
print('  Silchenkov:', len(sil_answers), distribution(sil_answers))
print('  Silchenkov index:', len(sil_index))
