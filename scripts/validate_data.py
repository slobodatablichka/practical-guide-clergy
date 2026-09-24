#!/usr/bin/env python3
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

tickets = load('data/ticket-questions.json')
topics = load('data/topics.json')
legacy_answers = load('data/answers.json')
legacy_book = load('data/book-index.json')
textbooks = load('data/textbooks.json')
status = load('data/relevance-status.json')

assert len(tickets) == 180, len(tickets)
assert len(topics) == 171, len(topics)
assert len(legacy_answers) == 171, len(legacy_answers)
assert len(legacy_book) == 556, len(legacy_book)
assert {x['ticket'] for x in tickets} == set(range(1, 31))

for n in range(1, 31):
    rows = [x for x in tickets if x['ticket'] == n]
    assert sorted(x['ticket_position'] for x in rows) == list(range(1, 7)), n

topic_ids = {x['topic_id'] for x in topics}
assert topic_ids == {x['topic_id'] for x in legacy_answers}
assert all(x['topic_id'] in topic_ids for x in tickets)

assert len(textbooks) == 2
assert [x['id'] for x in textbooks] == ['nefedov', 'silchenkov']

expected_index_counts = {'nefedov': 556, 'silchenkov': 309}

for book in textbooks:
    answers = load(book['answers_path'])
    index = load(book['index_path'])
    assert len(answers) == 171, (book['id'], len(answers))
    assert len(index) == expected_index_counts[book['id']], (book['id'], len(index))
    assert {x['topic_id'] for x in answers} == topic_ids
    assert all(1 <= int(x['relevance']) <= 5 for x in answers)
    assert all(x['short_answer'].strip() for x in answers)

    epub = ROOT / book['epub_path']
    with zipfile.ZipFile(epub) as zf:
        names = set(zf.namelist())
        for answer in answers:
            href = answer.get('epub_href')
            if href:
                assert href.split('#')[0] in names, (book['id'], href)
            if answer['relevance'] >= 2 and href:
                assert answer.get('source_fragments'), (book['id'], answer['topic_id'])

assert status['method'] == 'automatic_initial_v1'
assert set(status['books']) == {'nefedov', 'silchenkov'}

print('OK: 30 tickets, 180 positions, 171 topics; two textbook indexes and two complete answer sets with rel_1..rel_5.')
