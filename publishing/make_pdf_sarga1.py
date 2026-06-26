#!/usr/bin/env python3
"""Generate book-quality PDF – Ganapati Sambhavam Sarga 1."""

import re, urllib.request, yaml
from pathlib import Path
from html import escape as esc

BASE      = Path("telugu")
SARGA_DIR = BASE / "sarga-1"
FONTS_DIR = Path("fonts_cache")
FONTS_DIR.mkdir(exist_ok=True)
OUTPUT    = "ganapati_sambhavam_sarga1.pdf"
YAML_PATH = BASE / "meta_data" / "chapter_topics.yaml"

SKIP_SECTIONS = {"**పదచ్ఛేదము**"}

SECTION_MAP = {
    "**అన్వయము**":       ("anvaya",  "అన్వయము"),
    "**ప్రతిపదార్థము**":  ("pratipa", "ప్రతిపదార్థము"),
    "**భావము**":          ("bhava",   "భావము"),
}

FONT_URLS = {
    "Ponnala.ttf":
        "https://fonts.gstatic.com/s/ponnala/v3/w8gaH2QxQOU08bbbrQs.ttf",
    "TiroTelugu-Regular.ttf":
        "https://fonts.gstatic.com/s/tirotelugu/v7/aFTQ7PxlZWk2EPiSymjXdKSN.ttf",
    "TiroTelugu-Italic.ttf":
        "https://fonts.gstatic.com/s/tirotelugu/v7/aFTS7PxlZWk2EPiSymjXdJSPSK0.ttf",
}

# ── Fonts ─────────────────────────────────────────────────────────────────────
def download_fonts():
    for fname, url in FONT_URLS.items():
        fp = FONTS_DIR / fname
        if not fp.exists():
            print(f"  Downloading {fname}…", flush=True)
            urllib.request.urlretrieve(url, fp)
    print("  Fonts ready.")

# ── Inline markdown → HTML ────────────────────────────────────────────────────
def inline(text):
    text = re.sub(r'\\([=\-!.,:()\[\]/])', r'\1', text)
    parts = re.split(r'(\*\*[^*\n]+\*\*)', text)
    out = []
    for p in parts:
        if p.startswith('**') and p.endswith('**') and len(p) > 4:
            out.append(f'<strong>{esc(p[2:-2])}</strong>')
        else:
            out.append(esc(p))
    return ''.join(out)

# ── Topic file parser ─────────────────────────────────────────────────────────
def parse_topic(path):
    """
    Returns dict:
      image_src  – absolute path string or None
      image_alt  – alt text
      html       – full HTML of topic content (no image tag)
    """
    text     = path.read_text(encoding='utf-8')
    lines    = text.split('\n')
    buf      = []
    skipping = False
    state    = 'header'
    in_vb    = False    # inside <div class="verse-block">
    image_src, image_alt = None, None

    def close_vb():
        nonlocal in_vb
        if in_vb:
            buf.append('</div>')
            in_vb = False

    for line in lines:
        s = line.strip()
        if not s:
            continue

        # Title
        if s.startswith('# '):
            close_vb()
            buf.append(f'<h2 class="topic-title">{esc(s[2:])}</h2>')
            state = 'header'; skipping = False
            continue

        # Image – capture path for dedicated page, skip inline
        if s.startswith('!['):
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m and image_src is None:   # first image only
                image_src = str((SARGA_DIR / m.group(2)).resolve())
                image_alt = m.group(1)
            continue

        # Skip section
        if s in SKIP_SECTIONS:
            close_vb(); skipping = True; continue

        # Known section headers
        if s in SECTION_MAP:
            close_vb()
            new_state, label = SECTION_MAP[s]
            skipping = False; state = new_state
            buf.append(f'<div class="sec-hdr">{esc(label)}</div>')
            continue

        if skipping:
            continue

        # Bullet items
        if s.startswith('* '):
            buf.append(f'<div class="pratipa-item">{inline(s[2:])}</div>')
            continue

        # Bold lines
        if s.startswith('**') and s.endswith('**') and len(s) > 4:
            inner = s[2:-2]
            if '|' in inner:
                if not in_vb:
                    # Insert 1-line spacer after bhavamu before a new shloka
                    if state == 'bhava':
                        buf.append('<div class="bhava-spacer"></div>')
                    buf.append('<div class="verse-block">')
                    in_vb = True
                buf.append(f'<div class="verse">{inline(s)}</div>')
                state = 'verse'
            else:
                close_vb()
                buf.append(f'<div class="trans-label">{esc(inner)}</div>')
            continue

        # Plain text
        if state == 'header':
            buf.append(f'<p class="topic-desc">{inline(s)}</p>')
        else:
            buf.append(f'<p class="body-text">{inline(s)}</p>')

    close_vb()
    return {'image_src': image_src, 'image_alt': image_alt, 'html': ''.join(buf)}

# ── CSS ───────────────────────────────────────────────────────────────────────
def build_css(footer_left, footer_right_left, footer_right_right):
    fa = FONTS_DIR.resolve()
    # footer_left  = text for outer-left pages
    # For :left pages  → left=page-num,  right=sarga-name
    # For :right pages → left=sarga-name, right=page-num
    return f"""
@font-face {{
    font-family:'Ponnala';
    src:url('{fa}/Ponnala.ttf') format('truetype');
    font-weight:normal; font-style:normal;
}}
@font-face {{
    font-family:'TiroTelugu';
    src:url('{fa}/TiroTelugu-Regular.ttf') format('truetype');
    font-weight:normal; font-style:normal;
}}
@font-face {{
    font-family:'TiroTelugu';
    src:url('{fa}/TiroTelugu-Italic.ttf') format('truetype');
    font-weight:normal; font-style:italic;
}}

@page {{ size:5.5in 8.5in; }}

/* ── Left (even) pages: page-num outer-left, sarga-name outer-right ── */
@page :left {{
    margin:0.75in 0.65in 1.1in 0.9in;
    @bottom-left {{
        content: counter(page);
        font-family:'TiroTelugu',serif; font-size:9pt; color:#333;
        border-top:0.6pt solid #555; padding-top:5pt; margin-top:14pt;
        vertical-align:top;
    }}
    @bottom-center {{
        content:"";
        border-top:0.6pt solid #555; margin-top:14pt; padding-top:5pt;
        vertical-align:top;
    }}
    @bottom-right {{
        content:"{footer_left}";
        font-family:'TiroTelugu',serif; font-size:9pt; color:#333;
        border-top:0.6pt solid #555; padding-top:5pt; margin-top:14pt;
        vertical-align:top; text-align:right;
    }}
}}

/* ── Right (odd) pages: sarga-name outer-left, page-num outer-right ── */
@page :right {{
    margin:0.75in 0.9in 1.1in 0.65in;
    @bottom-left {{
        content:"{footer_left}";
        font-family:'TiroTelugu',serif; font-size:9pt; color:#333;
        border-top:0.6pt solid #555; padding-top:5pt; margin-top:14pt;
        vertical-align:top;
    }}
    @bottom-center {{
        content:"";
        border-top:0.6pt solid #555; margin-top:14pt; padding-top:5pt;
        vertical-align:top;
    }}
    @bottom-right {{
        content: counter(page);
        font-family:'TiroTelugu',serif; font-size:9pt; color:#333;
        border-top:0.6pt solid #555; padding-top:5pt; margin-top:14pt;
        vertical-align:top; text-align:right;
    }}
}}

/* ── Image pages: no footer, full margins ── */
@page img-pg {{
    size:5.5in 8.5in;
    margin:0.75in 0.75in 0.75in 0.75in;
    @bottom-left  {{ content:none; border:none; }}
    @bottom-center {{ content:none; border:none; }}
    @bottom-right {{ content:none; border:none; }}
}}

/* ── Base ── */
* {{ box-sizing:border-box; margin:0; padding:0; }}
html {{ font-size:10pt; }}
body {{
    font-family:'TiroTelugu',serif;
    font-size:10pt; line-height:1.45; color:#111;
}}

/* ── Sarga opening (top of first page) ── */
.sarga-hdr {{
    text-align:center;
    margin-bottom:0.3in;
    page-break-after:avoid;
}}
.sarga-invocation {{
    font-family:'TiroTelugu',serif;
    font-size:10pt; color:#444; margin-bottom:0.1in;
}}
.sarga-title-hdr {{
    font-family:'Ponnala',serif;
    font-size:22pt; line-height:1.25; color:#111;
    margin-bottom:0.5in;
}}
.sarga-desc {{
    font-family:'TiroTelugu',serif;
    font-size:10pt; line-height:1.45;
    color:#222; text-align:justify;
    max-width:4in; margin:0 auto;
}}

/* ── Dedicated image page ── */
.img-pg {{
    page:img-pg;
    page-break-before:always;
    page-break-after:always;
    text-align:center;
    padding-top:0.6in;
}}
.img-pg img {{
    max-width:3.8in;
    max-height:5.5in;
    display:block;
    margin:0 auto;
    border:2pt solid #444;
    padding:6pt;
}}
.img-caption {{
    font-size:9pt; font-style:italic;
    color:#555; margin-top:0.12in;
    text-align:center;
}}

/* ── Topic block ── */
.topic {{ margin-bottom:0.1in; }}
.topic-title {{
    font-family:'Ponnala',serif;
    font-size:14pt; font-weight:bold;
    line-height:1.3; color:#111;
    text-align:center;
    margin:0.3in 0 0.08in 0;
    page-break-after:avoid;
}}
.topic-desc {{
    font-style:italic; font-size:10pt;
    color:#444; margin:0 0 0.08in 0;
    line-height:1.45; text-align:center;
}}

/* ── Transition label ── */
.trans-label {{
    font-family:'Ponnala',serif;
    font-size:9pt; color:#555;
    margin:0.12in 0 0.04in 0;
    font-style:italic; text-align:center;
}}

/* ── Verse block (indented, space above and below) ── */
.verse-block {{
    margin-top:0.06in;
    margin-bottom:0.18in;
    padding-left:0.35in;
    page-break-inside:avoid;
}}
.verse {{
    font-family:'TiroTelugu',serif;
    font-weight:bold;
    font-size:10pt; line-height:1.55;
}}

/* ── Section headers (అన్వయము / ప్రతిపదార్థము / భావము) ── */
.sec-hdr {{
    font-family:'TiroTelugu',serif;
    font-weight:bold; font-size:12pt;
    color:#111; line-height:1.3;
    margin:0.08in 0 0.04in 0;
}}

/* ── Body text ── */
.body-text {{
    font-size:10pt; line-height:1.45;
    margin:0.02in 0;
}}

/* ── 1-line spacer after bhavamu before next shloka ── */
.bhava-spacer {{
    height:1.45em;
}}

/* ── ప్రతిపదార్థము items ── */
.pratipa-item {{
    font-size:9.5pt; line-height:1.38;
    margin:0.015in 0 0 0.12in;
}}
.pratipa-item strong {{
    font-weight:bold;
}}

/* ── End matter ── */
.end-matter {{
    text-align:center;
    margin-top:0.6in;
    padding-top:0.2in;
    border-top:0.5pt solid #aaa;
}}
.end-matter p {{
    font-size:10pt; line-height:1.6; color:#333; margin:0;
}}
"""

# ── Full HTML assembly ────────────────────────────────────────────────────────
def build_html(sarga_meta, topic_files):
    sarga_title = sarga_meta.get('title', sarga_meta['name'])
    sarga_desc  = sarga_meta.get('description', '')
    sarga_num   = sarga_meta['number']
    sarga_name  = sarga_meta['name']
    raw_em      = sarga_meta.get('end_matter', '')
    end_matter  = raw_em.replace('\\n', '\n')
    footer_txt  = f"సర్గ {sarga_num}  ·  {sarga_name}"

    css = build_css(footer_txt, footer_txt, footer_txt)

    # ── Sarga opening section (top of page 1) ──────────────────────────
    sarga_hdr = f"""<div class="sarga-hdr">
  <p class="sarga-invocation">అథ గణపతి సమ్భవాఽఽఖ్యే కావ్యే</p>
  <div class="sarga-title-hdr">{esc(sarga_title)}</div>
  <p class="sarga-desc">{esc(sarga_desc)}</p>
</div>"""

    # ── Topics ─────────────────────────────────────────────────────────
    body_parts = [sarga_hdr]
    for tf in topic_files:
        parsed = parse_topic(tf)

        # Dedicated image page (with border) before topic text
        if parsed['image_src']:
            img_html = (
                f'<div class="img-pg">'
                f'<img src="{parsed["image_src"]}" alt="{esc(parsed["image_alt"])}">'
                f'<p class="img-caption">{esc(parsed["image_alt"])}</p>'
                f'</div>'
            )
            body_parts.append(img_html)

        # Topic text (starts on new page if image precedes it)
        body_parts.append(f'<div class="topic">{parsed["html"]}</div>')

    # ── End matter ─────────────────────────────────────────────────────
    em_lines = [l.strip() for l in end_matter.strip().split('\n') if l.strip()]
    em_html  = '\n'.join(f'<p>{esc(l)}</p>' for l in em_lines)
    body_parts.append(f'<div class="end-matter">{em_html}</div>')

    return f"""<!DOCTYPE html>
<html lang="te">
<head><meta charset="UTF-8">
<style>{css}</style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>"""

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    print("Downloading fonts…")
    download_fonts()

    print("Reading YAML…")
    with open(YAML_PATH, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    sarga_meta = next(s for s in data['sargas'] if s['number'] == 1)

    topic_files = sorted(SARGA_DIR.glob("topic_*.md"))
    print(f"  {len(topic_files)} topics.")

    print("Building HTML…")
    html = build_html(sarga_meta, topic_files)
    Path("sarga1_preview.html").write_text(html, encoding='utf-8')

    print("Generating PDF…")
    from weasyprint import HTML as WP
    WP(string=html, base_url=str(Path.cwd())).write_pdf(OUTPUT)
    mb = Path(OUTPUT).stat().st_size / 1024 / 1024
    print(f"  Done → {OUTPUT}  ({mb:.1f} MB)")

if __name__ == '__main__':
    main()
