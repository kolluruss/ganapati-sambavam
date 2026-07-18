#!/usr/bin/env python3
"""
make_pdf_book_english_easyread.py — Ganapati Sambhavam PDF builder
(English/Devanagari "Easy Read" edition)

USAGE
-----
  python3.9 publishing/make_pdf_book_english_easyread.py

OUTPUT
------
  pdfs/ganapati_sambhavam_english_easyread.pdf

WHY THIS EDITION EXISTS
------------------------
The standard English edition (make_pdf_book_english.py) lays out each verse
group — Shloka, Anvaya, Meaning of Terms, Meaning — as one continuous flow.
This edition instead splits every verse group onto a forced two-page unit:

  ODD  (right-hand) page — the "read straight through" content:
       any transitional narrative before the verse, the Devanagari +
       IAST shloka, and the English Meaning.
  EVEN (left-hand)  page — the "glance at if you need it" content:
       Anvaya (word-order prose) and Meaning of Terms (word-by-word
       gloss).

A reader who only wants the story/translation can flip through odd pages
only; a reader who wants the grammatical detail can check the facing even
page. This forces a page break before every single verse group (791 of them
across the book), so this edition runs to many more pages than the standard
one — that is expected, not a bug.

Everything else (front matter, TOC, sarga dividers, back matter, covers)
reuses make_pdf_book_english.py unchanged; this script only reparses each
topic file into per-verse primary/secondary units instead of one flowing
block, and adds a small stylesheet forcing the odd/even placement.
"""

import argparse
import re
import yaml
from pathlib import Path
from html import escape as esc

from make_pdf_book_english import (
    REPO_ROOT, MD_BASE, TELUGU_BASE, IMG_DIR, CSS_FILE, YAML_PATH, OUTPUT_DIR,
    SARGA_THEMES, SKIP_SECTIONS, SECTION_MAP, DEVANAGARI_RE,
    download_fonts, build_dynamic_css, inline, _flush_shloka,
    parse_frontback_dir, build_toc, collect_topic_ids,
)

OUTPUT_FILENAME = "ganapati_sambhavam_english_easyread.pdf"


# ── Per-verse-unit topic parser ─────────────────────────────────────
# Same source format as make_pdf_book_english.parse_topic, but instead of
# one flowing HTML block, returns a list of {'primary', 'secondary'} units
# — one per Shloka group in the file.

def parse_topic_easyread(path, sarga_dir, topic_id):
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    title = path.stem

    units = []
    primary_buf, secondary_buf = [], []
    state = 'header'          # header | shloka | skip | anvaya | terms | bhava | trans
    deva_lines, iast_lines = [], []
    seen_h1 = [False]

    def flush_shloka():
        _flush_shloka(primary_buf, deva_lines, iast_lines)
        deva_lines.clear()
        iast_lines.clear()

    def flush_unit():
        if primary_buf or secondary_buf:
            units.append({
                'primary': ''.join(primary_buf),
                'secondary': ''.join(secondary_buf),
            })
        primary_buf.clear()
        secondary_buf.clear()

    for raw in lines:
        s = raw.strip()

        if s.startswith('# '):
            if state == 'shloka':
                flush_shloka()
            heading = re.sub(r'\*\*([^*]+)\*\*', r'\1', s[2:]).strip()
            if not seen_h1[0]:
                title = heading
                primary_buf.append(f'<h2 id="{topic_id}" class="topic-title">{esc(title)}</h2>')
                seen_h1[0] = True
            else:
                # Transitional narrative caption inserted between shlokas —
                # it introduces the *next* verse group, so it starts a new unit.
                flush_unit()
                primary_buf.append(f'<p class="topic-desc">{inline(heading)}</p>')
            state = 'header'
            continue

        if s.startswith('!['):
            if state == 'shloka':
                flush_shloka()
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                src = (sarga_dir / m.group(2)).resolve()
                if src.exists():
                    primary_buf.append(
                        f'<div class="img-pg"><img src="{src}" alt="{esc(m.group(1))}">'
                        f'<p class="img-caption">{esc(m.group(1))}</p></div>'
                    )
            continue

        if s.startswith('### '):
            if state == 'shloka':
                flush_shloka()
            label = s[4:].strip()
            if label == 'Shloka:':
                if state == 'bhava':
                    # Previous unit's Meaning just ended — this Shloka starts
                    # the next verse-group unit.
                    flush_unit()
                state = 'shloka'
                continue
            if label in SKIP_SECTIONS:
                state = 'skip'
                continue
            if label in SECTION_MAP:
                key, hdr_label, is_devanagari = SECTION_MAP[label]
                state = key
                target = secondary_buf if key in ('anvaya', 'terms') else primary_buf
                hdr_class = 'sec-hdr-deva' if is_devanagari else 'sec-hdr'
                target.append(f'<div class="{hdr_class}">{esc(hdr_label)}</div>')
                if key == 'bhava':
                    target.append('<div class="bhava-spacer"></div>')
                continue
            # Unrecognised H3 — transitional caption; starts the next unit.
            flush_unit()
            state = 'trans'
            primary_buf.append(f'<p class="topic-desc">{inline(label)}</p>')
            continue

        if not s:
            continue

        if state == 'shloka':
            (iast_lines if not DEVANAGARI_RE.search(s) else deva_lines).append(
                s[:-5].rstrip() if s.endswith('<br/>') else s
            )
            continue

        if state == 'skip' or state == 'trans':
            continue

        if state == 'terms' and s.startswith('* '):
            secondary_buf.append(f'<div class="pratipa-item">{inline(s[2:])}</div>')
            continue

        # anvaya/bhava/terms continuation prose, or header description
        target = secondary_buf if state in ('anvaya', 'terms') else primary_buf
        cls = 'topic-desc' if state == 'header' else 'body-text'
        target.append(f'<p class="{cls}">{inline(s)}</p>')

    if state == 'shloka':
        flush_shloka()
    flush_unit()

    return {'topic_id': topic_id, 'title': title, 'units': units}


def placeholder_topic_units(topic_id, num):
    html = (
        f'<h2 id="{topic_id}" class="topic-title">Topic {num} (pending translation)</h2>'
        f'<p class="body-text"><em>This section is not yet available in English — '
        f'translation is pending due to a temporary API quota limit. '
        f'See markdown/english/flagged_for_review.txt.</em></p>'
    )
    return [{'primary': html, 'secondary': ''}]


# ── Sarga HTML builder (easy-read layout) ───────────────────────────

def build_sarga_html_easyread(sarga_meta, sarga_dir, page_class):
    sarga_num = sarga_meta['number']
    sarga_id = f"sarga-{sarga_num}-hdr"
    sarga_title = sarga_meta['title']
    sarga_desc = sarga_meta['description']

    parts = [f"""<div class="{page_class}">
<div class="sarga-hdr">
  <p class="sarga-invocation">अथ गणपति सम्भवाख्ये काव्ये</p>
  <div id="{sarga_id}" class="sarga-title-hdr">{esc(sarga_title)}</div>
  <p class="sarga-desc">{esc(sarga_desc)}</p>
</div>"""]

    telugu_dir = TELUGU_BASE / f'sarga-{sarga_num}'
    expected_nums = sorted(
        int(re.search(r'topic_(\d+)', tf.stem).group(1))
        for tf in telugu_dir.glob('topic_*.md')
    )
    for num in expected_nums:
        tid = f"s{sarga_num}-t{num:02d}"
        tf = sarga_dir / f'topic_{num:02d}.md'
        if tf.exists():
            units = parse_topic_easyread(tf, sarga_dir, tid)['units']
        else:
            units = placeholder_topic_units(tid, num)
        for unit in units:
            parts.append(f'<div class="easyread-primary">{unit["primary"]}</div>')
            if unit['secondary'].strip():
                parts.append(f'<div class="easyread-secondary">{unit["secondary"]}</div>')

    parts.append('</div>')
    return '\n'.join(parts)


# ── Extra CSS: force the odd/even (right/left) page placement ───────

def build_easyread_css(vol_sargas):
    css = """
.easyread-primary   { break-before: right; page-break-before: right; }
.easyread-secondary { break-before: left;  page-break-before: left; }
"""
    for n in vol_sargas:
        css += f".sarga{n}-section {{ break-before: right; page-break-before: right; }}\n"
    return css


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build Ganapati Sambhavam English/Devanagari PDF — Easy Read edition (A4)"
    )
    parser.parse_args()

    output_path = OUTPUT_DIR / OUTPUT_FILENAME
    preview_path = OUTPUT_DIR / OUTPUT_FILENAME.replace(".pdf", "_preview.html")

    print(f"Output  : {output_path}")

    print("Checking fonts…")
    download_fonts()

    print("Reading sarga metadata…")
    with open(YAML_PATH, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    yaml_sargas = {s['number']: s for s in data['sargas']}

    sargas = {}
    for n in range(1, 11):
        name = yaml_sargas[n]['name_transliteration']
        sargas[n] = {
            'number': n,
            'name': name,
            'title': name,
            'description': SARGA_THEMES[n],
        }

    vol_sargas = list(range(1, 11))

    print("Parsing sarga-0 (front matter)…")
    s0_entries, s0_inners = parse_frontback_dir(MD_BASE / 'sarga-0')
    s0_html_parts = [f'<div class="front-matter-section">{inner}</div>' for inner in s0_inners]

    print("Parsing sarga-11 (back matter)…")
    s11_entries, s11_inners = parse_frontback_dir(MD_BASE / 'sarga-11')
    s11_html_parts = [f'<div class="back-matter-section">{inner}</div>' for inner in s11_inners]

    sarga_topic_ids = {}
    for n in vol_sargas:
        print(f"Parsing sarga-{n}…")
        sd = MD_BASE / f'sarga-{n}'
        sarga_topic_ids[n] = collect_topic_ids(sargas[n], sd)

    print("Building TOC…")
    toc_html = build_toc(s0_entries, [(sargas[n], sarga_topic_ids[n]) for n in vol_sargas], s11_entries)

    print("Building sarga bodies (per-verse odd/even units)…")
    sarga_html_parts = []
    for n in vol_sargas:
        sd = MD_BASE / f'sarga-{n}'
        sarga_html_parts.append(build_sarga_html_easyread(sargas[n], sd, f'sarga{n}-section'))

    dynamic_css = build_dynamic_css([sargas[n] for n in vol_sargas])
    easyread_css = build_easyread_css(vol_sargas)

    cover_front = IMG_DIR / 'cover_front_english.png'
    cover_back = IMG_DIR / 'cover_back_english.png'
    front_html = (f'<div class="cover-pg">'
                  f'<img src="{cover_front.as_uri()}" alt="front cover">'
                  f'</div>') if cover_front.exists() else ''
    back_html = (f'<div class="cover-pg">'
                 f'<img src="{cover_back.as_uri()}" alt="back cover">'
                 f'</div>') if cover_back.exists() else ''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Ganapati Sambhavam — English Edition (Easy Read)</title>
  <style>{dynamic_css}{easyread_css}</style>
</head>
<body>
{front_html}
{''.join(s0_html_parts)}
{toc_html}
{''.join(sarga_html_parts)}
{''.join(s11_html_parts)}
{back_html}
</body>
</html>"""

    OUTPUT_DIR.mkdir(exist_ok=True)
    preview_path.write_text(html, encoding='utf-8')
    print(f"Preview : {preview_path}")

    print("Generating PDF…")
    from weasyprint import HTML as WP, CSS
    stylesheets = [
        CSS(filename=str(CSS_FILE)),
        CSS(string=dynamic_css),
        CSS(string=easyread_css),
    ]
    WP(string=html, base_url=str(REPO_ROOT)).write_pdf(
        str(output_path), stylesheets=stylesheets
    )
    mb = output_path.stat().st_size / 1024 / 1024
    print(f"Done    : {output_path}  ({mb:.1f} MB)")


if __name__ == '__main__':
    main()
