#!/usr/bin/env python3
import json, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))

tickets=load('data/ticket-questions.json')
topics=load('data/topics.json')
answers=load('data/answers.json')
book=load('data/book-index.json')
assert len(tickets)==180, len(tickets)
assert len(topics)==171, len(topics)
assert len(answers)==171, len(answers)
assert len(book)==556, len(book)
assert {x['ticket'] for x in tickets}==set(range(1,31))
for n in range(1,31):
    rows=[x for x in tickets if x['ticket']==n]
    assert sorted(x['ticket_position'] for x in rows)==list(range(1,7)), n
ids={x['topic_id'] for x in topics}
assert ids=={x['topic_id'] for x in answers}
assert all(x['topic_id'] in ids for x in tickets)
assert all(x['short_answer'].strip() for x in answers)

epub=ROOT/'assets/book/taintstva-i-obryady-pravoslavnoy-tserkvi.epub'
with zipfile.ZipFile(epub) as z:
    names=set(z.namelist())
    for x in tickets:
        assert x['epub_href'].split('#')[0] in names, x['epub_href']

print('OK: 30 tickets, 180 positions, 171 topics, 171 answers, 556 textbook entries; all EPUB targets exist.')
