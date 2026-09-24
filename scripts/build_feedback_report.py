#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

REQUIRED = ["Имя", "Вопрос", "Учебник", "rel", "Оценка"]


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def read_csv(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    if not rows:
        raise SystemExit("CSV пуст: нет строк с отзывами.")
    headers = rows[0].keys()
    missing = [h for h in REQUIRED if h not in headers]
    if missing:
        raise SystemExit("В CSV отсутствуют обязательные колонки: " + ", ".join(missing))
    return rows


def to_int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def pct(part, whole):
    return 0 if not whole else round(part * 100 / whole, 1)


def svg_bar_chart(labels, values, title, max_value=None, width=760, height=330):
    if not labels:
        return '<div class="empty">Недостаточно данных для диаграммы.</div>'
    pad_l, pad_r, pad_t, pad_b = 52, 20, 48, 58
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    maxv = max_value if max_value is not None else max(values) if values else 1
    maxv = max(maxv, 1)
    gap = 16
    bar_w = max(18, (plot_w - gap * (len(labels) + 1)) / len(labels))
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    parts.append(f'<text x="{pad_l}" y="26" class="chart-title">{esc(title)}</text>')
    for i in range(6):
        y = pad_t + plot_h - (plot_h * i / 5)
        val = maxv * i / 5
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width-pad_r}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" class="axis">{val:.1f}</text>')
    for i, (lab, val) in enumerate(zip(labels, values)):
        x = pad_l + gap + i * (bar_w + gap)
        bh = plot_h * val / maxv
        y = pad_t + plot_h - bh
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="7" class="bar"/>')
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{max(y-8, pad_t+12):.1f}" text-anchor="middle" class="value">{esc(round(val,2))}</text>')
        label = str(lab)
        if len(label) > 18:
            label = label[:17] + "…"
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{height-28}" text-anchor="middle" class="axis">{esc(label)}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def svg_horizontal_bars(items, title, width=920, row_h=44):
    if not items:
        return '<div class="empty">Недостаточно данных для диаграммы.</div>'
    items = items[:10]
    height = 64 + row_h * len(items)
    label_w = 360
    plot_w = width - label_w - 70
    maxv = max(v for _, v in items) or 1
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    out.append(f'<text x="16" y="28" class="chart-title">{esc(title)}</text>')
    for i, (label, value) in enumerate(items):
        y = 54 + i * row_h
        short = label if len(label) <= 52 else label[:51] + "…"
        out.append(f'<text x="16" y="{y+17}" class="axis label">{esc(short)}</text>')
        bw = plot_w * value / maxv
        out.append(f'<rect x="{label_w}" y="{y}" width="{bw:.1f}" height="24" rx="6" class="bar"/>')
        out.append(f'<text x="{label_w+bw+8:.1f}" y="{y+17}" class="value">{value}</text>')
    out.append('</svg>')
    return ''.join(out)


def svg_heatmap(matrix, title, width=610, height=520):
    maxv = max(matrix.values()) if matrix else 0
    if maxv == 0:
        return '<div class="empty">Недостаточно данных для диаграммы.</div>'
    x0, y0, cell = 110, 70, 70
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    out.append(f'<text x="20" y="30" class="chart-title">{esc(title)}</text>')
    for rating in range(1, 6):
        out.append(f'<text x="{x0+(rating-1)*cell+cell/2}" y="{y0-16}" text-anchor="middle" class="axis">Оц. {rating}</text>')
    for rel in range(5, 0, -1):
        row = 5-rel
        out.append(f'<text x="{x0-18}" y="{y0+row*cell+cell/2+5}" text-anchor="end" class="axis">rel_{rel}</text>')
        for rating in range(1, 6):
            val = matrix.get((rel, rating), 0)
            opacity = 0.08 + 0.82 * (val / maxv)
            x = x0+(rating-1)*cell
            y = y0+row*cell
            out.append(f'<rect x="{x}" y="{y}" width="{cell-6}" height="{cell-6}" rx="8" class="heat" style="opacity:{opacity:.3f}"/>')
            out.append(f'<text x="{x+(cell-6)/2}" y="{y+(cell-6)/2+5}" text-anchor="middle" class="heat-text">{val}</text>')
    out.append('</svg>')
    return ''.join(out)


def build_analysis(rows):
    clean = []
    for r in rows:
        rating = to_int(r.get("Оценка"))
        rel = to_int(r.get("rel"))
        if not 1 <= rating <= 5 or not 1 <= rel <= 5:
            continue
        clean.append({**r, "_rating": rating, "_rel": rel})
    if not clean:
        raise SystemExit("В CSV нет корректных оценок 1–5.")

    n = len(clean)
    avg = mean(r["_rating"] for r in clean)
    names = {r.get("Имя", "").strip() for r in clean if r.get("Имя", "").strip()}
    questions = {r.get("Вопрос", "").strip() for r in clean if r.get("Вопрос", "").strip()}
    comments = [r for r in clean if r.get("Комментарий", "").strip()]
    critical = [r for r in clean if r["_rating"] <= 2]

    rating_counts = Counter(r["_rating"] for r in clean)
    book_groups = defaultdict(list)
    question_groups = defaultdict(list)
    heat = Counter()
    for r in clean:
        book_groups[r.get("Учебник", "Не указано")].append(r)
        key = (r.get("Вопрос", ""), r.get("Учебник", ""))
        question_groups[key].append(r)
        heat[(r["_rel"], r["_rating"])] += 1

    book_stats = []
    for book, rs in sorted(book_groups.items()):
        book_stats.append({
            "book": book,
            "count": len(rs),
            "avg": mean(x["_rating"] for x in rs),
            "comments": sum(1 for x in rs if x.get("Комментарий", "").strip()),
        })

    qstats = []
    for (q, book), rs in question_groups.items():
        qstats.append({
            "question": q,
            "book": book,
            "count": len(rs),
            "avg": mean(x["_rating"] for x in rs),
            "rel": round(mean(x["_rel"] for x in rs), 2),
            "comments": sum(1 for x in rs if x.get("Комментарий", "").strip()),
        })
    qstats.sort(key=lambda x: (-x["count"], x["avg"], x["question"]))

    low = sorted(qstats, key=lambda x: (x["avg"], -x["count"], x["question"]))[:10]
    mismatch_highrel_lowrating = [x for x in qstats if x["rel"] >= 4 and x["avg"] <= 3]
    mismatch_lowrel_highrating = [x for x in qstats if x["rel"] <= 2 and x["avg"] >= 4]

    if n < 10:
        confidence = "Данных пока очень мало. Все выводы ниже — только ориентиры, а не устойчивая статистика."
    elif n < 30:
        confidence = "Данных уже достаточно для первых сигналов, но выводы пока предварительные."
    else:
        confidence = "Объём данных позволяет видеть устойчивые тенденции, хотя отдельные вопросы всё равно нужно оценивать по числу отзывов."

    conclusions = [
        confidence,
        f"Средняя пользовательская оценка: {avg:.2f} из 5 по {n} отзывам.",
        f"Комментарии оставлены в {pct(len(comments), n):.1f}% отзывов ({len(comments)} из {n}).",
    ]
    if critical:
        conclusions.append(f"Оценок 1–2: {len(critical)} ({pct(len(critical), n):.1f}%). Их стоит проверять в первую очередь.")
    else:
        conclusions.append("Оценок 1–2 пока нет.")
    if len(book_stats) >= 2:
        ordered = sorted(book_stats, key=lambda x: x["avg"], reverse=True)
        diff = ordered[0]["avg"] - ordered[-1]["avg"]
        conclusions.append(f"Разница средней оценки между учебниками сейчас составляет {diff:.2f} балла; при малом числе отзывов её нельзя считать окончательной.")
    if mismatch_highrel_lowrating:
        conclusions.append(f"Есть {len(mismatch_highrel_lowrating)} сочетаний «высокий rel / низкая пользовательская оценка» — полезный список для редакторской проверки.")
    if mismatch_lowrel_highrating:
        conclusions.append(f"Есть {len(mismatch_lowrel_highrating)} сочетаний «низкий rel / высокая пользовательская оценка» — возможно, текущий rel стоит пересмотреть.")

    return {
        "rows": clean,
        "n": n,
        "avg": avg,
        "names": names,
        "questions": questions,
        "comments": comments,
        "critical": critical,
        "rating_counts": rating_counts,
        "book_stats": book_stats,
        "qstats": qstats,
        "low": low,
        "heat": heat,
        "mismatch_highrel_lowrating": mismatch_highrel_lowrating,
        "mismatch_lowrel_highrating": mismatch_lowrel_highrating,
        "conclusions": conclusions,
    }


def kpi_cards(a):
    vals = [
        ("Отзывов", a["n"]),
        ("Участников*", len(a["names"])),
        ("Вопросов", len(a["questions"])),
        ("Средняя оценка", f'{a["avg"]:.2f} / 5'),
        ("С комментариями", f'{pct(len(a["comments"]), a["n"]):.1f}%'),
        ("Оценки 1–2", len(a["critical"])),
    ]
    return ''.join(
        f'<div class="kpi"><div class="kpi-label">{esc(k)}</div><div class="kpi-value">{esc(v)}</div></div>'
        for k, v in vals
    )


def qtable(items, heading):
    if not items:
        return f'<section><h2>{esc(heading)}</h2><div class="empty">Пока нет таких сигналов.</div></section>'
    rows = ''.join(
        '<tr>'
        f'<td>{esc(x["question"])}</td><td>{esc(x["book"])}</td><td>{x["count"]}</td>'
        f'<td>{x["rel"]}</td><td>{x["avg"]:.2f}</td><td>{x["comments"]}</td>'
        '</tr>'
        for x in items[:15]
    )
    return (
        f'<section><h2>{esc(heading)}</h2><div class="table-wrap"><table>'
        '<thead><tr><th>Вопрос</th><th>Учебник</th><th>Отзывов</th><th>rel</th>'
        f'<th>Средняя оценка</th><th>Комментариев</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    )


def comments_section(rows):
    commented = [r for r in rows if r.get("Комментарий", "").strip()]
    commented.sort(key=lambda r: r.get("Обновлено", r.get("Создано", "")), reverse=True)
    if not commented:
        return '<section><h2>Комментарии</h2><div class="empty">Комментариев пока нет.</div></section>'
    cards = []
    for r in commented[:40]:
        cards.append(
            '<article class="comment-card">'
            f'<div class="comment-meta"><strong>{esc(r.get("Имя"))}</strong> · {esc(r.get("Учебник"))} · '
            f'оценка {r["_rating"]} · rel_{r["_rel"]}</div>'
            f'<div class="comment-question">{esc(r.get("Вопрос"))}</div>'
            f'<blockquote>{esc(r.get("Комментарий"))}</blockquote>'
            '</article>'
        )
    return '<section><h2>Комментарии</h2><div class="comments">' + ''.join(cards) + '</div></section>'


def raw_table(rows):
    cols = ["Имя", "Вопрос", "Учебник", "rel", "Оценка", "Комментарий", "Раздел", "Билет", "Позиция", "Создано", "Обновлено"]
    head = ''.join(f'<th>{esc(c)}</th>' for c in cols)
    body = []
    for r in rows:
        body.append('<tr>' + ''.join(f'<td>{esc(r.get(c, ""))}</td>' for c in cols) + '</tr>')
    return (
        '<section><div class="section-head"><h2>Все отзывы</h2>'
        '<input id="filter" type="search" placeholder="Фильтр по таблице…" oninput="filterRows()"></div>'
        f'<div class="table-wrap"><table id="allRows"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'
    )


def build_html(source: Path, analysis):
    now = datetime.now().astimezone().strftime("%d.%m.%Y %H:%M")
    books = analysis["book_stats"]
    book_chart = svg_bar_chart(
        [x["book"] for x in books],
        [x["avg"] for x in books],
        "Средняя оценка по учебникам",
        max_value=5,
    )
    counts = [analysis["rating_counts"].get(i, 0) for i in range(1, 6)]
    rating_chart = svg_bar_chart(
        [str(i) for i in range(1, 6)],
        counts,
        "Распределение пользовательских оценок",
        max_value=max(counts) if counts else 1,
    )
    top_chart = svg_horizontal_bars(
        [(x["question"], x["count"]) for x in analysis["qstats"]],
        "Вопросы с наибольшим числом отзывов",
    )
    heatmap = svg_heatmap(analysis["heat"], "rel учебника × пользовательская оценка")
    conclusions = ''.join(f'<li>{esc(x)}</li>' for x in analysis["conclusions"])

    css = r'''
:root{--bg:#f3f5f2;--card:#fff;--text:#20251f;--muted:#677065;--accent:#315846;--accent2:#86a795;--border:#d9dfd8;--danger:#9a3e35;--shadow:0 10px 28px rgba(30,45,35,.08)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}.wrap{max-width:1180px;margin:auto;padding:28px 20px 56px}.hero{background:linear-gradient(135deg,#fff,#edf3ee);border:1px solid var(--border);border-radius:22px;padding:28px;box-shadow:var(--shadow)}.eyebrow{text-transform:uppercase;letter-spacing:.1em;font-size:12px;font-weight:800;color:var(--muted)}h1{font-size:clamp(30px,5vw,48px);line-height:1.05;margin:8px 0 10px}h2{font-size:24px;margin:0 0 14px}p{margin:6px 0}.muted{color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin:18px 0}.kpi{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;box-shadow:var(--shadow)}.kpi-label{font-size:12px;color:var(--muted);font-weight:700}.kpi-value{font-size:24px;font-weight:850;margin-top:3px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}section{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:20px;margin-top:16px;box-shadow:var(--shadow)}.analysis{border-left:5px solid var(--accent)}.analysis li{margin:7px 0}.chart{overflow:auto;background:#fbfcfb;border:1px solid #e6ebe6;border-radius:14px;padding:8px}.chart svg{width:100%;height:auto;min-width:480px}.chart-title{font-size:17px;font-weight:800;fill:#20251f}.grid{stroke:#e5e9e5;stroke-width:1}.axis{font-size:12px;fill:#667066}.axis.label{font-size:11.5px}.bar{fill:#315846}.value{font-size:12px;font-weight:800;fill:#315846}.heat{fill:#315846}.heat-text{font-size:15px;font-weight:850;fill:#1f2d25}.table-wrap{overflow:auto;border:1px solid var(--border);border-radius:12px}table{border-collapse:collapse;width:100%;min-width:820px}th,td{padding:10px 11px;border-bottom:1px solid #e8ece8;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#edf2ee;color:#304038;font-size:12px}tr:hover td{background:#fafcfb}.comments{display:grid;gap:10px}.comment-card{border:1px solid var(--border);border-radius:12px;padding:13px;background:#fbfcfb}.comment-meta{font-size:12px;color:var(--muted)}.comment-question{font-weight:800;margin-top:4px}.comment-card blockquote{margin:8px 0 0;padding-left:12px;border-left:3px solid var(--accent2);white-space:pre-wrap}.empty{padding:18px;border:1px dashed #cdd5cd;border-radius:12px;color:var(--muted);background:#fafbfa}.section-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.section-head input{min-width:280px;border:1px solid #bcc8bf;border-radius:10px;padding:9px 11px;font:inherit}.foot{font-size:12px;color:var(--muted);margin-top:18px}
@media(max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}.grid2{grid-template-columns:1fr}}
@media(max-width:560px){.wrap{padding:14px 10px 40px}.hero,section{padding:15px;border-radius:14px}.kpis{grid-template-columns:repeat(2,1fr)}.section-head{align-items:stretch;flex-direction:column}.section-head input{min-width:0;width:100%}}
@media print{body{background:#fff}.wrap{max-width:none;padding:0}.hero,section,.kpi{box-shadow:none;break-inside:avoid}.section-head input{display:none}}
'''
    js = r'''function filterRows(){const q=document.getElementById('filter').value.toLowerCase();document.querySelectorAll('#allRows tbody tr').forEach(tr=>{tr.style.display=tr.innerText.toLowerCase().includes(q)?'':'none';});}'''

    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Отчёт по оценкам ответов</title><style>{css}</style></head><body><div class="wrap">'
        '<header class="hero"><div class="eyebrow">Практическое руководство для священнослужителя</div>'
        '<h1>Отчёт по оценкам ответов</h1>'
        f'<p>Автоматический отчёт по файлу <strong>{esc(source.name)}</strong>.</p>'
        f'<p class="muted">Сформирован {esc(now)}. *Число участников определяется по указанному имени/псевдониму.</p></header>'
        f'<div class="kpis">{kpi_cards(analysis)}</div>'
        f'<section class="analysis"><h2>Предварительный анализ</h2><ul>{conclusions}</ul></section>'
        f'<div class="grid2"><section><div class="chart">{rating_chart}</div></section><section><div class="chart">{book_chart}</div></section></div>'
        f'<div class="grid2"><section><div class="chart">{heatmap}</div></section><section><div class="chart">{top_chart}</div></section></div>'
        f'{qtable(analysis["low"], "Ответы с наиболее низкой средней оценкой")}'
        f'{qtable(analysis["mismatch_highrel_lowrating"], "Сигнал: высокий rel, но низкая пользовательская оценка")}'
        f'{qtable(analysis["mismatch_lowrel_highrating"], "Сигнал: низкий rel, но высокая пользовательская оценка")}'
        f'{comments_section(analysis["rows"])}'
        f'{raw_table(analysis["rows"])}'
        '<div class="foot">Этот файл содержит пользовательские имена/псевдонимы и комментарии. '
        'Не публикуйте его в открытом репозитории без отдельного решения.</div>'
        f'</div><script>{js}</script></body></html>'
    )


def main():
    parser = argparse.ArgumentParser(
        description="Преобразует CSV отзывов Supabase в автономный HTML-отчёт с диаграммами и предварительным анализом."
    )
    parser.add_argument("csv", type=Path, help="CSV, выгруженный из public.feedback_analysis")
    parser.add_argument("-o", "--output", type=Path, help="Путь к HTML-отчёту")
    args = parser.parse_args()

    source = args.csv
    if not source.exists():
        raise SystemExit(f"Файл не найден: {source}")

    output = args.output or source.with_name("feedback-report.html")
    rows = read_csv(source)
    analysis = build_analysis(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(source, analysis), encoding="utf-8")

    print(f"Готово: {output}")
    print(
        f"Отзывов: {analysis['n']}; средняя оценка: {analysis['avg']:.2f}; "
        f"комментариев: {len(analysis['comments'])}"
    )


if __name__ == "__main__":
    main()
