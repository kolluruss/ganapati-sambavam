#!/usr/bin/env python3
"""
make_pdf_book_english.py — Ganapati Sambhavam PDF builder (English/Devanagari edition)

USAGE
-----
  python3.9 publishing/make_pdf_book_english.py

OUTPUT
------
  pdfs/ganapati_sambhavam_english.pdf

Mirrors publishing/make_pdf_book.py's overall structure (dynamic @page CSS
with running sarga-name footers, TOC with page-number targets, WeasyPrint
render) but parses the English topic-file format instead of the Telugu one:

  # Topic Title                              -> topic heading
  ### Shloka:                                 -> Devanagari verse + IAST verse
  ### पदच्छेदम् (Padacchedam):                 -> omitted from the PDF (kept in
                                                  the markdown source only)
  ### अन्वयः (Anvaya):                         -> Devanagari prose
  ### Meaning of Terms:                       -> bulleted "term  = meaning"
  ### Meaning:                                -> English prose
  ### <anything else>                         -> transitional narrative
                                                  caption the model sometimes
                                                  inserts between shlokas

Some content is still missing (see markdown/english/flagged_for_review.txt)
because of Gemini API daily-quota exhaustion during translation; those
topics render with a placeholder note rather than blocking the whole build.
"""

import argparse
import re
import urllib.request
import yaml
from pathlib import Path
from html import escape as esc

# ── Paths (all absolute, relative to this script) ─────────────────

SCRIPT_DIR = Path(__file__).resolve().parent          # publishing/
REPO_ROOT  = SCRIPT_DIR.parent                        # ganapati-sambavam/
MD_BASE    = REPO_ROOT / "markdown" / "english"       # markdown/english/
TELUGU_BASE = REPO_ROOT / "markdown" / "telugu"       # for sarga metadata only
IMG_DIR    = REPO_ROOT / "images"                     # images/ (shared across languages)
FONTS_DIR  = SCRIPT_DIR / "fonts_cache"               # publishing/fonts_cache/
CSS_FILE   = SCRIPT_DIR / "book_english.css"          # publishing/book_english.css
YAML_PATH  = TELUGU_BASE / "meta_data" / "chapter_topics.yaml"
OUTPUT_DIR = REPO_ROOT / "pdfs"

OUTPUT_FILENAME = "ganapati_sambhavam_english.pdf"
PAGE_SIZE = "8.27in 11.69in"  # A4, matching the Telugu edition's combined --vol all
MARGINS = dict(inner="1.1in", outer="0.8in", top="0.9in", bottom="1.25in")

# English theme summaries per sarga (from README.md's Sarga Overview table),
# paired with the Sanskrit sarga name transliteration already present in the
# Telugu yaml. No separate English metadata file exists yet.
SARGA_THEMES = {
    1:  "The Himalayas, Kashmir, and Nepal — a geographical panorama.",
    2:  "The wedding of Shiva and Parvati.",
    3:  "Parvati creates Ganesha from clay using yogic power.",
    4:  "The debate between Shiva and the boy, and the beheading.",
    5:  "The elephant-head transplant and Ganesha's childhood.",
    6:  "The confrontation with Parashurama and the loss of one tusk.",
    7:  "Ganesha serves as scribe of the Mahabharata for Vyasa.",
    8:  "The divine modaka, and the circumambulation of his parents.",
    9:  "Ganesha's form as a metaphor for democratic governance.",
    10: "The poet's autobiography and his other works.",
}

SKIP_SECTIONS = {"पदच्छेदम् (Padacchedam):"}
SECTION_MAP = {
    "अन्वयः (Anvaya):":    ("anvaya", "अन्वयः (Anvaya)", True),
    "Meaning of Terms:":  ("terms",  "Meaning of Terms", False),
    "Meaning:":           ("bhava",  "Meaning", False),
}

DEVANAGARI_RE = re.compile(r'[ऀ-ॿ]')


# ── Font download (Google Fonts CSS2 API) ─────────────────────────

FONT_SPECS = {
    "NotoSerifDevanagari-Regular.ttf": ("Noto+Serif+Devanagari", "wght@400"),
    "NotoSerifDevanagari-Bold.ttf":    ("Noto+Serif+Devanagari", "wght@700"),
    "NotoSerif-Regular.ttf":           ("Noto+Serif", "wght@400"),
    "NotoSerif-Bold.ttf":              ("Noto+Serif", "wght@700"),
    "NotoSerif-Italic.ttf":            ("Noto+Serif", "ital,wght@1,400"),
}


def _resolve_font_url(family_param, axis_query):
    api = f"https://fonts.googleapis.com/css2?family={family_param}:{axis_query}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    css = urllib.request.urlopen(req).read().decode()
    m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
    return m.group(1) if m else None


def download_fonts():
    FONTS_DIR.mkdir(exist_ok=True)
    for fname, (family_param, axis_query) in FONT_SPECS.items():
        fp = FONTS_DIR / fname
        if fp.exists():
            continue
        print(f"  Fetching {fname}…", flush=True)
        url = _resolve_font_url(family_param, axis_query)
        if url:
            urllib.request.urlretrieve(url, fp)
        else:
            print(f"  WARNING: could not resolve URL for {fname}")
    print("  Fonts ready.")


# ── Dynamic CSS (@page rules with sarga names in footers) ────────

FOOTER_STYLE = (
    "font-family:'Noto Serif',serif; font-size:8pt; color:#333;"
    "padding-top:5pt; margin-top:14pt; vertical-align:top;"
)

def _page_rules(page_name, footer_txt, inner, outer, top, bottom):
    return f"""
@page {page_name}:left {{
    margin: {top} {outer} {bottom} {inner};
    @bottom-left  {{ content: counter(page); {FOOTER_STYLE} }}
    @bottom-right {{ content: "{footer_txt}"; {FOOTER_STYLE} text-align: right; }}
}}
@page {page_name}:right {{
    margin: {top} {inner} {bottom} {outer};
    @bottom-left  {{ content: "{footer_txt}"; {FOOTER_STYLE} }}
    @bottom-right {{ content: counter(page); {FOOTER_STYLE} text-align: right; }}
}}"""


def build_font_face_css():
    def f(name):
        return (FONTS_DIR / name).as_uri()
    return f"""
@font-face {{ font-family: 'Noto Serif Devanagari'; src: url('{f("NotoSerifDevanagari-Regular.ttf")}') format('truetype'); font-weight: normal; font-style: normal; }}
@font-face {{ font-family: 'Noto Serif Devanagari'; src: url('{f("NotoSerifDevanagari-Bold.ttf")}') format('truetype'); font-weight: bold; font-style: normal; }}
@font-face {{ font-family: 'Noto Serif'; src: url('{f("NotoSerif-Regular.ttf")}') format('truetype'); font-weight: normal; font-style: normal; }}
@font-face {{ font-family: 'Noto Serif'; src: url('{f("NotoSerif-Bold.ttf")}') format('truetype'); font-weight: bold; font-style: normal; }}
@font-face {{ font-family: 'Noto Serif'; src: url('{f("NotoSerif-Italic.ttf")}') format('truetype'); font-weight: normal; font-style: italic; }}
"""


def build_dynamic_css(sargas_meta):
    m = MARGINS
    css = build_font_face_css()
    css += f"@page {{ size: {PAGE_SIZE}; }}\n"
    css += f"@page cover-pg {{ size: {PAGE_SIZE}; margin: 0; }}\n"
    pg_w, pg_h = PAGE_SIZE.split()
    css += f".cover-pg {{ width: {pg_w}; height: {pg_h}; }}\n"
    css += _page_rules('front-matter-pg', 'Ganapati Sambhavam', m['inner'], m['outer'], m['top'], m['bottom'])
    css += _page_rules('back-matter-pg',  'Ganapati Sambhavam', m['inner'], m['outer'], m['top'], m['bottom'])
    css += _page_rules('toc-pg',          'Contents',           m['inner'], m['outer'], m['top'], m['bottom'])
    for sm in sargas_meta:
        n = sm['number']
        ft = f"Sarga {n}  ·  {sm['name']}"
        css += _page_rules(f'sarga{n}-pg', ft, m['inner'], m['outer'], m['top'], m['bottom'])
    return css


# ── Inline helpers ─────────────────────────────────────────────────

def inline(text):
    """Convert **bold** and *italic* markdown to HTML (escaping everything else)."""
    parts = re.split(r'(\*\*[^*\n]+\*\*|\*[^*\n]+\*)', text)
    out = []
    for p in parts:
        if p.startswith('**') and p.endswith('**') and len(p) > 4:
            out.append(f'<strong>{esc(p[2:-2])}</strong>')
        elif p.startswith('*') and p.endswith('*') and len(p) > 2:
            out.append(f'<em>{esc(p[1:-1])}</em>')
        else:
            out.append(esc(p))
    return ''.join(out)


# ── English topic parser ──────────────────────────────────────────

def _flush_shloka(buf, deva_lines, iast_lines):
    if not deva_lines and not iast_lines:
        return
    buf.append('<div class="verse-block">')
    if deva_lines:
        buf.append(f'<div class="verse-deva">{"<br/>".join(inline(l) for l in deva_lines)}</div>')
    if iast_lines:
        buf.append(f'<div class="verse-iast">{"<br/>".join(inline(l) for l in iast_lines)}</div>')
    buf.append('</div>')


def parse_topic(path, sarga_dir, topic_id):
    """Parse an English topic .md file. Returns dict with topic_id, title,
    image_src, image_alt, html."""
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    buf = []
    title = path.stem
    image_src = image_alt = None

    state = 'header'          # header | shloka | skip | anvaya | terms | bhava | trans
    deva_lines, iast_lines = [], []
    seen_h1 = [False]

    def flush_shloka():
        _flush_shloka(buf, deva_lines, iast_lines)
        deva_lines.clear()
        iast_lines.clear()

    for raw in lines:
        s = raw.strip()

        if s.startswith('# '):
            if state == 'shloka':
                flush_shloka()
            heading = re.sub(r'\*\*([^*]+)\*\*', r'\1', s[2:]).strip()
            if not seen_h1[0]:
                title = heading
                buf.append(f'<h2 id="{topic_id}" class="topic-title">{esc(title)}</h2>')
                seen_h1[0] = True
            else:
                # The model occasionally inserts extra H1s mid-file as
                # transitional narrative captions instead of the intended
                # single top-of-file heading — render as a caption, not a
                # second title (which would otherwise clobber the TOC entry).
                buf.append(f'<p class="topic-desc">{inline(heading)}</p>')
            state = 'header'
            continue

        if s.startswith('!['):
            if state == 'shloka':
                flush_shloka()
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                src = (sarga_dir / m.group(2)).resolve()
                if src.exists():
                    if image_src is None:
                        image_src = str(src)
                        image_alt = m.group(1)
                    buf.append(
                        f'<div class="img-pg"><img src="{src}" alt="{esc(m.group(1))}">'
                        f'<p class="img-caption">{esc(m.group(1))}</p></div>'
                    )
            continue

        if s.startswith('### '):
            if state == 'shloka':
                flush_shloka()
            label = s[4:].strip()
            if label == 'Shloka:':
                state = 'shloka'
                continue
            if label in SKIP_SECTIONS:
                state = 'skip'
                continue
            if label in SECTION_MAP:
                key, hdr_label, is_devanagari = SECTION_MAP[label]
                state = key
                hdr_class = 'sec-hdr-deva' if is_devanagari else 'sec-hdr'
                buf.append(f'<div class="{hdr_class}">{esc(hdr_label)}</div>')
                if key == 'bhava':
                    buf.append('<div class="bhava-spacer"></div>')
                continue
            # Unrecognised H3 — a transitional narrative caption the model
            # inserted between shlokas; render like a small heading.
            state = 'trans'
            buf.append(f'<p class="topic-desc">{inline(label)}</p>')
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
            buf.append(f'<div class="pratipa-item">{inline(s[2:])}</div>')
            continue

        # anvaya / bhava / terms continuation prose, or header description
        cls = 'topic-desc' if state == 'header' else 'body-text'
        buf.append(f'<p class="{cls}">{inline(s)}</p>')

    if state == 'shloka':
        flush_shloka()

    return {
        'topic_id': topic_id,
        'title': title,
        'image_src': image_src,
        'image_alt': image_alt,
        'html': ''.join(buf),
    }


def placeholder_topic_html(topic_id, num):
    return (
        f'<div class="topic"><h2 id="{topic_id}" class="topic-title">'
        f'Topic {num} (pending translation)</h2>'
        f'<p class="body-text"><em>This section is not yet available in English — '
        f'translation is pending due to a temporary API quota limit. '
        f'See markdown/english/flagged_for_review.txt.</em></p></div>'
    )


# ── English sarga-0 (front matter) parser ─────────────────────────
# Front matter uses inline bold labels/verses (like the Telugu original)
# rather than the H3 headings of the main topic files: bold Devanagari
# verse lines, italic IAST lines beneath them, and inline labels like
# "**Anvaya:** <content>", "**Word Meanings:**", "**Meaning:** <content>".

S0_LABELS = {'Anvaya:': 'sec-hdr-deva', 'Word Meanings:': 's0-sec-hdr', 'Meaning:': 's0-sec-hdr'}


def parse_sarga0_file(path):
    """Convert an English sarga-0 markdown file to HTML. Returns (sec_id, title, html)."""
    s0_dir = path.parent
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    buf = []
    sec_id = path.stem
    title = path.stem
    in_verse_block = False
    verse_start = None
    img_count = 0

    def close_verse():
        # Merge the open verse-block's fragments (opening tag + however many
        # verse/iast lines) into a single buf entry, so each buf item is a
        # self-contained unit — needed by the gallery post-pass below, which
        # pairs up whole caption/image units rather than raw fragments.
        nonlocal in_verse_block, verse_start
        if in_verse_block:
            merged = ''.join(buf[verse_start:]) + '</div>'
            del buf[verse_start:]
            buf.append(merged)
            in_verse_block = False
            verse_start = None

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        if s == '---':
            close_verse()
            buf.append('<hr class="s0-hr">')
            continue

        if s.startswith('### '):
            close_verse()
            buf.append(f'<h3 class="s0-h3">{inline(s[4:])}</h3>')
            continue
        if s.startswith('## '):
            close_verse()
            buf.append(f'<h2 class="s0-h2">{inline(s[3:])}</h2>')
            continue
        if s.startswith('# '):
            close_verse()
            raw_title = re.sub(r'\*\*([^*]+)\*\*', r'\1', s[2:]).strip()
            title = raw_title
            buf.append(f'<h1 id="{sec_id}" class="s0-title">{inline(s[2:])}</h1>')
            continue

        if s.startswith('!['):
            close_verse()
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                src = (s0_dir / m.group(2)).resolve()
                if src.exists():
                    img_count += 1
                    buf.append(
                        f'<div class="s0-img"><img src="{src}" alt="{esc(m.group(1))}">'
                        f'<p class="img-caption">{esc(m.group(1))}</p></div>'
                    )
            continue

        # Inline bold section label, e.g. "**Anvaya:** ..." / "**Meaning:** ..."
        matched_label = None
        for label in S0_LABELS:
            if s.startswith(f'**{label}**'):
                matched_label = label
                break
        if matched_label:
            close_verse()
            css_cls = S0_LABELS[matched_label]
            buf.append(f'<div class="{css_cls}">{esc(matched_label[:-1])}</div>')
            rest = s[len(f'**{matched_label}**'):].strip()
            if rest:
                buf.append(f'<p class="body-text">{inline(rest)}</p>')
            continue

        # Word-meaning bullet: "* term  = meaning"
        if s.startswith('* '):
            close_verse()
            buf.append(f'<div class="pratipa-item">{inline(s[2:])}</div>')
            continue
        # Plain bullet
        if s.startswith('- '):
            close_verse()
            buf.append(f'<div class="s0-bullet">{inline(s[2:])}</div>')
            continue

        # Attribution caption, e.g. "— Kumarasambhavam"
        if s.startswith('—'):
            close_verse()
            buf.append(f'<p class="s0-attribution">{esc(s)}</p>')
            continue

        # Fully-bold single line: either a Devanagari verse pada, or a
        # bold caption (e.g. family-photo captions, "Thus," / "Yours,").
        if s.startswith('**') and s.endswith('**') and len(s) > 4:
            inner_txt = s[2:-2]
            if DEVANAGARI_RE.search(inner_txt):
                if not in_verse_block:
                    verse_start = len(buf)
                    buf.append('<div class="s0-verse-block">')
                    in_verse_block = True
                buf.append(f'<div class="s0-verse">{esc(inner_txt)}</div>')
            else:
                close_verse()
                buf.append(f'<p class="s0-bold">{inline(s)}</p>')
            continue

        # Fully-italic single line: the IAST transliteration under a verse pada
        if s.startswith('*') and s.endswith('*') and not s.startswith('**') and len(s) > 2:
            if not in_verse_block:
                verse_start = len(buf)
                buf.append('<div class="s0-verse-block">')
                in_verse_block = True
            buf.append(f'<div class="s0-verse-iast">{esc(s[1:-1])}</div>')
            continue

        close_verse()
        buf.append(f'<p class="s0-body">{inline(s)}</p>')

    close_verse()

    if title == path.stem and img_count > 1 and len(buf) > 1:
        # Multi-photo gallery file (no top-level heading, more than one
        # image): group each caption+image pair that follows the title into
        # one wrapper cell, so CSS can tile them (e.g. 2x2). Single-image
        # "no-h1" files (e.g. an author bio with one portrait) are left
        # alone here and keep the plain centered .s0-gallery styling.
        head, rest = buf[0], buf[1:]
        cells, i = [], 0
        while i < len(rest) - 1:
            cells.append(f'<div class="family-cell">{rest[i]}{rest[i + 1]}</div>')
            i += 2
        if i < len(rest):
            cells.append(f'<div class="family-cell">{rest[i]}</div>')
        return sec_id, title, head + ''.join(cells)

    return sec_id, title, ''.join(buf)


def parse_frontback_dir(dir_path):
    """Parse all markdown files in a front/back-matter-style directory
    (sarga-0 or sarga-11: prose narrative pages plus optional no-h1
    photo-gallery pages, in the same inline-bold-label format). Returns
    (entries, inner_html_parts): entries is the [(sec_id, title), ...]
    list of TOC-worthy pages (those with a real heading); inner_html_parts
    is the per-file HTML, already wrapped in its .s0-gallery/.s0-photo-grid
    div where applicable — the caller still needs to wrap each in its own
    page-section div (front-matter-section / back-matter-section)."""
    entries = []
    inner_parts = []
    if not dir_path.is_dir():
        return entries, inner_parts
    for sf in sorted(dir_path.glob('*.md')):
        sec_id, entry_title, content = parse_sarga0_file(sf)
        if entry_title != sf.stem:  # skip gallery/image-only files (no H1 heading)
            entries.append((sec_id, entry_title))
        if entry_title == sf.stem:
            # No-h1 file: either a multi-photo grid (family-cell markup
            # present -> tile it) or a single-image page (e.g. author
            # bio) -> plain centered gallery styling.
            gallery_cls = 's0-gallery s0-photo-grid' if 'family-cell' in content else 's0-gallery'
            inner = f'<div class="{gallery_cls}">{content}</div>'
        else:
            inner = content
        inner_parts.append(inner)
    return entries, inner_parts


# ── TOC builder ───────────────────────────────────────────────────

def build_toc(s0_entries, sargas_topics, s11_entries=()):
    lines = ['<div class="toc-section"><h1 class="toc-heading">Table of Contents</h1>']
    if s0_entries:
        lines.append('<div class="toc-sarga-hdr">Front Matter</div>')
        for sec_id, entry_title in s0_entries:
            lines.append(
                f'<div class="toc-entry">'
                f'<a href="#{sec_id}">{esc(entry_title)}</a>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-pgnum"><a href="#{sec_id}"></a></span>'
                f'</div>'
            )
    for sarga_meta, topics in sargas_topics:
        sarga_id = f"sarga-{sarga_meta['number']}-hdr"
        lines.append(
            f'<div class="toc-entry">'
            f'<a href="#{sarga_id}" style="font-weight:bold;font-size:11pt;">'
            f'Sarga {sarga_meta["number"]} · {esc(sarga_meta["name"])}</a>'
            f'<span class="toc-dots"></span>'
            f'<span class="toc-pgnum"><a href="#{sarga_id}"></a></span>'
            f'</div>'
        )
        for topic_id, topic_title in topics:
            lines.append(
                f'<div class="toc-entry toc-l2">'
                f'<a href="#{topic_id}">{esc(topic_title)}</a>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-pgnum"><a href="#{topic_id}"></a></span>'
                f'</div>'
            )
    if s11_entries:
        lines.append('<div class="toc-sarga-hdr">Back Matter</div>')
        for sec_id, entry_title in s11_entries:
            lines.append(
                f'<div class="toc-entry">'
                f'<a href="#{sec_id}">{esc(entry_title)}</a>'
                f'<span class="toc-dots"></span>'
                f'<span class="toc-pgnum"><a href="#{sec_id}"></a></span>'
                f'</div>'
            )
    lines.append('</div>')
    return '\n'.join(lines)


# ── Sarga HTML builder ────────────────────────────────────────────

def build_sarga_html(sarga_meta, sarga_dir, page_class):
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
            parsed = parse_topic(tf, sarga_dir, tid)
            parts.append(f'<div class="topic">{parsed["html"]}</div>')
        else:
            parts.append(placeholder_topic_html(tid, num))

    parts.append('</div>')
    return '\n'.join(parts)


def collect_topic_ids(sarga_meta, sarga_dir):
    sarga_num = sarga_meta['number']
    telugu_dir = TELUGU_BASE / f'sarga-{sarga_num}'
    expected_nums = sorted(
        int(re.search(r'topic_(\d+)', tf.stem).group(1))
        for tf in telugu_dir.glob('topic_*.md')
    )
    ids = []
    for num in expected_nums:
        tid = f"s{sarga_num}-t{num:02d}"
        tf = sarga_dir / f'topic_{num:02d}.md'
        if tf.exists():
            ids.append((tid, parse_topic(tf, sarga_dir, tid)['title']))
        else:
            ids.append((tid, f"Topic {num} (pending translation)"))
    return ids


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build Ganapati Sambhavam English/Devanagari PDF (A4)")
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

    sarga_html_parts = []
    for n in vol_sargas:
        sd = MD_BASE / f'sarga-{n}'
        sarga_html_parts.append(build_sarga_html(sargas[n], sd, f'sarga{n}-section'))

    dynamic_css = build_dynamic_css([sargas[n] for n in vol_sargas])

    cover_front = IMG_DIR / 'cover_front_english.png'
    cover_back  = IMG_DIR / 'cover_back_english.png'
    front_html  = (f'<div class="cover-pg">'
                   f'<img src="{cover_front.as_uri()}" alt="front cover">'
                   f'</div>') if cover_front.exists() else ''
    back_html   = (f'<div class="cover-pg">'
                   f'<img src="{cover_back.as_uri()}" alt="back cover">'
                   f'</div>') if cover_back.exists() else ''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Ganapati Sambhavam — English Edition</title>
  <style>{dynamic_css}</style>
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
    ]
    WP(string=html, base_url=str(REPO_ROOT)).write_pdf(
        str(output_path), stylesheets=stylesheets
    )
    mb = output_path.stat().st_size / 1024 / 1024
    print(f"Done    : {output_path}  ({mb:.1f} MB)")


if __name__ == '__main__':
    main()
