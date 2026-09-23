#!/usr/bin/env python3
import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PAGE = "https://azbyka.ru/otechnik/Gennadij_Nefedov/tainstva-i-obrjady-pravoslavnoj-tserkvi/"
OUT = Path(__file__).resolve().parents[1] / "assets/book/taintstva-i-obryady-pravoslavnoy-tserkvi.epub"
OUT.parent.mkdir(parents=True, exist_ok=True)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 practical-guide-clergy/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.geturl(), r.headers.get_content_type()

page, final_url, _ = get(PAGE)
text = page.decode("utf-8", errors="ignore")
hrefs = [html.unescape(x) for x in re.findall(r'''href\s*=\s*["']([^"']+)["']''', text, re.I)]

candidates = []
for href in hrefs:
    u = urllib.parse.urljoin(final_url, href)
    low = u.lower()
    if "epub" in low or "download" in low:
        candidates.append(u)

# Common fallback: some book sites expose download links through query params.
candidates += [
    PAGE + "?download=epub",
    PAGE.rstrip("/") + ".epub",
]

seen=set()
for url in candidates:
    if url in seen: continue
    seen.add(url)
    try:
        data, resolved, ctype = get(url)
    except Exception as e:
        print("skip", url, e)
        continue
    # EPUB is a ZIP container and therefore starts with PK.
    if data.startswith(b"PK") and b"application/epub+zip" in data[:2000]:
        OUT.write_bytes(data)
        print("Downloaded EPUB:", resolved, len(data), "bytes")
        sys.exit(0)
    print("not epub", resolved, ctype, len(data))

raise SystemExit("Could not locate a valid EPUB download on the source page")
