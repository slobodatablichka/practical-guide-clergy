#!/usr/bin/env python3
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EPUB = ROOT / 'assets/book/taintstva-i-obryady-pravoslavnoy-tserkvi.epub'
OUT_JSON = ROOT / 'data/book-index.json'
OUT_MD = ROOT / 'docs/BOOK-TOC.md'
NS = {'n':'http://www.daisy.org/z3986/2005/ncx/'}

with zipfile.ZipFile(EPUB) as z:
    root = ET.fromstring(z.read('toc.ncx'))
    items = []

    def walk(node, chapter=None, depth=0):
        title = node.find('n:navLabel/n:text', NS).text.strip()
        href = node.find('n:content', NS).attrib['src']
        order = int(node.attrib.get('playOrder', 0))
        if title.startswith('Глава '):
            chapter = title
        try:
            raw = z.read(href.split('#')[0])
            text = ' '.join(BeautifulSoup(raw, 'html.parser').stripped_strings)
        except Exception:
            text = ''
        items.append({
            'order': order,
            'depth': depth,
            'title': title,
            'href': href,
            'chapter': chapter,
            'text': text,
        })
        for child in node.findall('n:navPoint', NS):
            walk(child, chapter, depth + 1)

    nav_map = root.find('n:navMap', NS)
    for node in nav_map.findall('n:navPoint', NS):
        walk(node)

items.sort(key=lambda x: x['order'])
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
with OUT_MD.open('w', encoding='utf-8') as f:
    f.write('# Оглавление учебника\n\n')
    for item in items:
        indent = '  ' * item['depth']
        f.write(f"{item['order']:03d}. {indent}{item['title']} — \`{item['href']}\`\n")

print(f'Indexed {len(items)} EPUB navigation entries.')
