#!/usr/bin/env python3
"""
make_pdf_book.py — Ganapati Sambhavam PDF builder

USAGE
-----
  python3.9 publishing/make_pdf_book.py --vol 1        # sargas 1-5  → vol1 PDF
  python3.9 publishing/make_pdf_book.py --vol 2        # sargas 6-10 → vol2 PDF
  python3.9 publishing/make_pdf_book.py --vol all      # sargas 1-10 → combined PDF

OUTPUT
------
  pdfs/ganapati_sambhavam_vol1.pdf
  pdfs/ganapati_sambhavam_vol2.pdf
  pdfs/ganapati_sambhavam.pdf

CSS
---
  Static layout rules live in publishing/book.css.
  Dynamic @page rules (Telugu sarga names in footers) are generated
  inline by build_dynamic_css() and injected alongside book.css.
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
MD_BASE    = REPO_ROOT / "markdown" / "telugu"        # markdown/telugu/
IMG_DIR    = REPO_ROOT / "images"                     # images/
FONTS_DIR  = SCRIPT_DIR / "fonts_cache"               # publishing/fonts_cache/
CSS_FILE   = SCRIPT_DIR / "book.css"                  # publishing/book.css
YAML_PATH  = MD_BASE / "meta_data" / "chapter_topics.yaml"
OUTPUT_DIR = REPO_ROOT / "pdfs"

GDRIVE_FOLDER_ID = "16VenM_V9VNMFQScM5H5s3WZJLb8APP6b"  # images source on Google Drive

# page_size: Demy octavo for vol-1/2/demy, A4 for combined
# margins: (inner, outer, top, bottom) — inner = spine side
# compact_pratipa: if True, ప్రతిపదార్థము items are comma-separated (saves pages)
DEMY_MARGINS = dict(inner="0.9in",  outer="0.65in", top="0.75in", bottom="1.1in")
VOL_CONFIG = {
    "1":    (list(range(1, 6)),   "ganapati_sambhavam_vol1.pdf",  "Vol. 1 (సర్గలు 1–5)",
             "5.5in 8.5in",   DEMY_MARGINS, False),
    "2":    (list(range(6, 11)), "ganapati_sambhavam_vol2.pdf",  "Vol. 2 (సర్గలు 6–10)",
             "5.5in 8.5in",   DEMY_MARGINS, False),
    "all":  (list(range(1, 11)), "ganapati_sambhavam.pdf",       "సంపూర్ణ గ్రంథము (సర్గలు 1–10)",
             "8.27in 11.69in", dict(inner="1.1in", outer="0.8in", top="0.9in", bottom="1.25in"), False),
    "demy": (list(range(1, 11)), "ganapati_sambhavam_demy.pdf",  "సంపూర్ణ గ్రంథము (సర్గలు 1–10)",
             "5.5in 8.5in",   DEMY_MARGINS, True),
}

FONT_URLS = {
    "Ponnala.ttf":
        "https://fonts.gstatic.com/s/ponnala/v3/w8gaH2QxQOU08bbbrQs.ttf",
    "Gidugu.ttf":
        "https://fonts.gstatic.com/s/gidugu/v21/L0x8DFMkk1Sn6gFLJBKv.ttf",
}

GFONT_FAMILIES = {}

SKIP_SECTIONS = {"**పదచ్ఛేదము**"}
SECTION_MAP   = {
    "**అన్వయము**":       ("anvaya",  "అన్వయము"),
    "**ప్రతిపదార్థము**":  ("pratipa", "ప్రతిపదార్థము"),
    "**భావము**":          ("bhava",   "భావము"),
}


# ── Font download ──────────────────────────────────────────────────

def _resolve_gfont_url(family, weight):
    """Fetch the .ttf URL for a Google Font family+weight via the CSS2 API."""
    api = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}"
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    css = urllib.request.urlopen(req).read().decode()
    m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
    return m.group(1) if m else None


def _system_font_dir():
    """Return the user-level font directory fontconfig reads on this OS."""
    import platform
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Fonts"
    return Path.home() / ".fonts"


def _install_system_font(src: Path) -> bool:
    """Copy font into the system user-font directory so Pango/fontconfig can find it.
    WeasyPrint uses Pango for Telugu shaping; Pango finds fonts via fontconfig, not CSS @font-face.
    Returns True if the font was newly installed."""
    import shutil
    dest_dir = _system_font_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"  Installed {src.name} → {dest_dir}", flush=True)
        return True
    return False


def download_fonts():
    import platform, subprocess, shutil
    FONTS_DIR.mkdir(exist_ok=True)
    any_installed = False
    for fname, url in FONT_URLS.items():
        fp = FONTS_DIR / fname
        if not fp.exists():
            print(f"  Downloading {fname}…", flush=True)
            urllib.request.urlretrieve(url, fp)
        any_installed |= _install_system_font(fp)
    for fname, (family, weight) in GFONT_FAMILIES.items():
        fp = FONTS_DIR / fname
        if not fp.exists():
            print(f"  Fetching {fname} from Google Fonts…", flush=True)
            url = _resolve_gfont_url(family, weight)
            if url:
                urllib.request.urlretrieve(url, fp)
            else:
                print(f"  WARNING: could not resolve URL for {fname}")
        any_installed |= _install_system_font(fp)
    if any_installed and platform.system() != "Darwin":
        subprocess.run(["fc-cache", "-fv", str(_system_font_dir())],
                       capture_output=True)
    print("  Fonts ready.")


# ── Google Drive image sync ───────────────────────────────────────

def _ensure_packages(*packages):
    import sys
    _pkg_imports = {
        "google-api-python-client": "googleapiclient",
    }
    for pkg in packages:
        import_name = _pkg_imports.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            print(f"  Installing {pkg}…", flush=True)
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])


def sync_images_from_gdrive(force: bool = False):
    """Download all images from the Google Drive folder into images/.
    Requires GOOGLE_API_KEY env var; the Drive folder must be shared as
    'Anyone with the link' (Viewer).
    """
    import os
    existing = list(IMG_DIR.glob("*.png"))
    if existing and not force:
        print(f"  Images cached: {len(existing)} files in {IMG_DIR}")
        return

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  WARNING: GOOGLE_API_KEY not set — skipping image download")
        return

    _ensure_packages("google-api-python-client")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io

    IMG_DIR.mkdir(exist_ok=True)
    service = build("drive", "v3", developerKey=api_key)

    print(f"  Downloading images from Drive folder {GDRIVE_FOLDER_ID}…", flush=True)
    files, page_token = [], None
    while True:
        resp = service.files().list(
            q=f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    pngs = [f for f in files if f["name"].endswith(".png")]
    print(f"  Found {len(pngs)} images", flush=True)
    for f in pngs:
        dest = IMG_DIR / f["name"]
        req  = service.files().get_media(fileId=f["id"])
        buf  = io.FileIO(dest, mode="wb")
        dl   = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        print(f"    {f['name']}", flush=True)
    print(f"  Downloaded {len(pngs)} images.")


# ── Dynamic CSS (@page rules with Telugu sarga names) ─────────────

FOOTER_STYLE = (
    "font-family:'Gidugu',sans-serif; font-size:8pt; color:#333;"
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
    """Return @font-face rules with absolute file:// paths.
    Using absolute paths guarantees WeasyPrint finds the fonts
    regardless of how the HTML string or base_url is configured."""
    def f(name):
        return (FONTS_DIR / name).as_uri()   # file:///absolute/path/to/font.ttf
    return f"""
@font-face {{
    font-family: 'Ponnala';
    src: url('{f("Ponnala.ttf")}') format('truetype');
    font-weight: normal; font-style: normal;
}}
@font-face {{
    font-family: 'Gidugu';
    src: url('{f("Gidugu.ttf")}') format('truetype');
    font-weight: normal; font-style: normal;
}}
"""


def build_dynamic_css(sargas_meta, page_size, margins):
    """Generate font-face + page-size + @page rules with Telugu sarga names in running footers."""
    m = margins
    css = build_font_face_css()
    css += f"@page {{ size: {page_size}; }}\n"
    css += f"@page cover-pg {{ size: {page_size}; margin: 0; }}\n"

    # Give .cover-pg explicit dimensions so height:100% on img resolves correctly.
    pg_w, pg_h = page_size.split()
    css += f".cover-pg {{ width: {pg_w}; height: {pg_h}; }}\n"

    # Single position:fixed rule draws one unbroken horizontal line across every page
    # at the top of the bottom-margin area.  z-index is auto (0), so .cover-pg
    # (z-index:1) renders on top and hides the line on cover pages.
    css += (
        f".footer-line-rule {{\n"
        f"    position: fixed; left: 0; right: 0;\n"
        f"    bottom: calc({m['bottom']} - 14pt);\n"
        f"    height: 0; border-top: 0.6pt solid #555;\n"
        f"}}\n"
    )

    css += _page_rules('front-matter-pg', 'గణపతి సంభవమ్',    m['inner'], m['outer'], m['top'], m['bottom'])
    css += _page_rules('toc-pg',          'విషయానుక్రమణిక', m['inner'], m['outer'], m['top'], m['bottom'])
    for sm in sargas_meta:
        n  = sm['number']
        ft = f"సర్గ {n}  ·  {sm['name']}"
        css += _page_rules(f'sarga{n}-pg', ft, m['inner'], m['outer'], m['top'], m['bottom'])
    return css


# ── Inline helpers ─────────────────────────────────────────────────

def inline(text):
    """Convert **bold** markdown and clean backslash escapes to HTML."""
    text = re.sub(r'\\([=\-!.,:()\[\]/])', r'\1', text)
    parts = re.split(r'(\*\*[^*\n]+\*\*)', text)
    out = []
    for p in parts:
        if p.startswith('**') and p.endswith('**') and len(p) > 4:
            out.append(f'<strong>{esc(p[2:-2])}</strong>')
        else:
            out.append(esc(p))
    return ''.join(out)


def slug(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)[:40]


# ── Sarga-0 (front matter) parser ────────────────────────────────

def parse_sarga0_file(path):
    """Convert a sarga-0 markdown file to HTML. Returns (sec_id, title, html)."""
    sarga0_dir = path.parent
    text  = path.read_text(encoding='utf-8')
    text  = text.replace('** **', '**\n**')
    lines = text.split('\n')
    buf   = []
    sec_id  = path.stem
    title   = path.stem
    state   = 'body'
    in_vb   = False
    skipping = False

    def close_vb():
        nonlocal in_vb
        if in_vb:
            buf.append('</div>')
            in_vb = False

    for line in lines:
        s = line.strip()
        if not s:
            continue

        if s.startswith('### '):
            close_vb()
            buf.append(f'<h3 class="s0-h3">{inline(s[4:])}</h3>')
            continue
        if s.startswith('## '):
            close_vb()
            buf.append(f'<h2 class="s0-h2">{inline(s[3:])}</h2>')
            continue
        if s.startswith('# '):
            close_vb()
            raw_title = re.sub(r'\*\*([^*]+)\*\*', r'\1', s[2:])
            title = raw_title.strip()
            buf.append(f'<h1 id="{sec_id}" class="s0-title">{inline(s[2:])}</h1>')
            state = 'body'; skipping = False
            continue

        if s.startswith('!['):
            close_vb()
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                src = (sarga0_dir / m.group(2)).resolve()
                if src.exists():
                    buf.append(
                        f'<div class="s0-img">'
                        f'<img src="{src}" alt="{esc(m.group(1))}">'
                        f'<p class="img-caption">{esc(m.group(1))}</p>'
                        f'</div>'
                    )
            continue

        if s in SKIP_SECTIONS:
            close_vb(); skipping = True; continue

        if s in SECTION_MAP:
            close_vb()
            _, label = SECTION_MAP[s]
            skipping = False; state = 'section'
            buf.append(f'<div class="sec-hdr">{esc(label)}</div>')
            continue

        if skipping:
            continue

        if s.startswith('- ') or s.startswith('* '):
            close_vb()
            buf.append(f'<div class="s0-bullet">{inline(s[2:])}</div>')
            continue

        if s.startswith('**') and s.endswith('**') and len(s) > 4:
            inner_txt = s[2:-2]
            if '|' in inner_txt:
                if not in_vb:
                    buf.append('<div class="verse-block">')
                    in_vb = True
                buf.append(f'<div class="verse">{inline(s)}</div>')
                state = 'verse'
            else:
                close_vb()
                buf.append(f'<p class="s0-bold">{inline(s)}</p>')
            continue

        close_vb()
        if state == 'section':
            buf.append(f'<p class="body-text">{inline(s)}</p>')
        else:
            buf.append(f'<p class="s0-body">{inline(s)}</p>')

    close_vb()
    return sec_id, title, ''.join(buf)


# ── Sarga topic parser ────────────────────────────────────────────

def parse_topic(path, sarga_dir, topic_id, compact_pratipa=False):
    """Parse a topic .md file. Returns dict with topic_id, title, image_src, image_alt, html."""
    text  = path.read_text(encoding='utf-8')
    text  = text.replace('** **', '**\n**')
    lines = text.split('\n')
    buf   = []
    title = path.stem
    skipping  = False
    state     = 'header'
    in_vb     = False
    image_src = image_alt = None
    pratipa_items = []   # accumulates items in compact pratipa mode

    def close_vb():
        nonlocal in_vb
        if in_vb:
            buf.append('</div>')
            in_vb = False

    def flush_pratipa():
        if compact_pratipa and pratipa_items:
            buf.append(
                f'<p class="pratipa-compact">{",  ".join(pratipa_items)}</p>'
            )
            pratipa_items.clear()

    for line in lines:
        s = line.strip()
        if not s:
            continue

        if s.startswith('# '):
            close_vb()
            flush_pratipa()
            title = re.sub(r'\*\*([^*]+)\*\*', r'\1', s[2:]).strip()
            buf.append(f'<h2 id="{topic_id}" class="topic-title">{esc(title)}</h2>')
            state = 'header'; skipping = False
            continue

        if s.startswith('!['):
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', s)
            if m:
                src = (sarga_dir / m.group(2)).resolve()
                if src.exists():
                    if image_src is None:
                        image_src = str(src)
                        image_alt = m.group(1)
                    buf.append(
                        f'<div class="img-pg">'
                        f'<img src="{src}" alt="{esc(m.group(1))}">'
                        f'<p class="img-caption">{esc(m.group(1))}</p>'
                        f'</div>'
                    )
            continue

        if s in SKIP_SECTIONS:
            close_vb(); flush_pratipa(); skipping = True; continue

        if s in SECTION_MAP:
            close_vb()
            flush_pratipa()
            _, label = SECTION_MAP[s]
            skipping = False; state = label
            buf.append(f'<div class="sec-hdr">{esc(label)}</div>')
            continue

        if skipping:
            continue

        if s.startswith('* '):
            if compact_pratipa and state == 'ప్రతిపదార్థము':
                pratipa_items.append(inline(s[2:]))
            else:
                buf.append(f'<div class="pratipa-item">{inline(s[2:])}</div>')
            continue

        if s.startswith('**') and s.endswith('**') and len(s) > 4:
            inner_txt = s[2:-2]
            if '|' in inner_txt:
                if not in_vb:
                    if state == 'భావము':
                        buf.append('<div class="bhava-spacer"></div>')
                    buf.append('<div class="verse-block">')
                    in_vb = True
                buf.append(f'<div class="verse">{inline(s)}</div>')
                state = 'verse'
            else:
                close_vb()
                buf.append(f'<div class="trans-label">{esc(inner_txt)}</div>')
            continue

        if state == 'header':
            buf.append(f'<p class="topic-desc">{inline(s)}</p>')
        else:
            buf.append(f'<p class="body-text">{inline(s)}</p>')

    close_vb()
    flush_pratipa()
    return {
        'topic_id':  topic_id,
        'title':     title,
        'image_src': image_src,
        'image_alt': image_alt,
        'html':      ''.join(buf),
    }


# ── TOC builder ───────────────────────────────────────────────────

def build_toc(s0_entries, sargas_topics):
    lines = ['<div class="toc-section"><h1 class="toc-heading">విషయానుక్రమణిక</h1>']
    lines.append('<div class="toc-sarga-hdr">ముందుమాట మరియు పీఠికలు</div>')
    for sec_id, title in s0_entries:
        lines.append(
            f'<div class="toc-entry">'
            f'<a href="#{sec_id}">{esc(title)}</a>'
            f'<span class="toc-dots"></span>'
            f'<span class="toc-pgnum"><a href="#{sec_id}"></a></span>'
            f'</div>'
        )
    for sarga_meta, topics in sargas_topics:
        sarga_id = f"sarga-{sarga_meta['number']}-hdr"
        lines.append(
            f'<div class="toc-entry">'
            f'<a href="#{sarga_id}" style="font-family:\'Ponnala\',serif;font-size:11pt;">'
            f'సర్గ {sarga_meta["number"]} · {esc(sarga_meta["name"])}</a>'
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
    lines.append('</div>')
    return '\n'.join(lines)


# ── Sarga HTML builder ────────────────────────────────────────────

def build_sarga_html(sarga_meta, topic_files, sarga_dir, page_class, compact_pratipa=False):
    sarga_title = sarga_meta.get('title', sarga_meta['name'])
    sarga_desc  = sarga_meta.get('description', '')
    raw_em      = sarga_meta.get('end_matter', '')
    end_matter  = raw_em.replace('\\n', '\n')
    sarga_num   = sarga_meta['number']
    sarga_id    = f"sarga-{sarga_num}-hdr"

    parts = [f"""<div class="{page_class}">
<div class="sarga-hdr">
  <p class="sarga-invocation">అథ గణపతి సమ్భవాఽఽఖ్యే కావ్యే</p>
  <div id="{sarga_id}" class="sarga-title-hdr">{esc(sarga_title)}</div>
  <p class="sarga-desc">{esc(sarga_desc)}</p>
</div>"""]

    for tf in topic_files:
        num    = int(re.search(r'topic_(\d+)', tf.stem).group(1))
        tid    = f"s{sarga_num}-t{num:02d}"
        parsed = parse_topic(tf, sarga_dir, tid, compact_pratipa=compact_pratipa)

        parts.append(f'<div class="topic">{parsed["html"]}</div>')

    if end_matter.strip():
        em_lines = [l.strip() for l in end_matter.strip().split('\n') if l.strip()]
        em_html  = '\n'.join(f'<p>{esc(l)}</p>' for l in em_lines)
        parts.append(f'<div class="end-matter">{em_html}</div>')

    parts.append('</div>')
    return '\n'.join(parts)


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build Ganapati Sambhavam PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3.9 publishing/make_pdf_book.py --vol 1\n"
            "  python3.9 publishing/make_pdf_book.py --vol 2\n"
            "  python3.9 publishing/make_pdf_book.py --vol all\n"
        ),
    )
    parser.add_argument(
        "--vol", required=True, choices=["1", "2", "all", "demy"],
        help=("1 = sargas 1-5 (Demy), 2 = sargas 6-10 (Demy), "
              "all = complete book (A4), demy = complete book (Demy, compact ప్రతిపదార్థము)")
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="Skip Google Drive image download (use locally cached images)"
    )
    parser.add_argument(
        "--force-download", action="store_true",
        help="Re-download images from Google Drive even if already cached"
    )
    args = parser.parse_args()

    vol_sargas, output_filename, vol_label, page_size, margins, compact_pratipa = VOL_CONFIG[args.vol]
    output_path  = OUTPUT_DIR / output_filename
    preview_path = OUTPUT_DIR / output_filename.replace(".pdf", "_preview.html")

    print(f"Building: {vol_label}")
    print(f"Sargas  : {vol_sargas}")
    print(f"Output  : {output_path}")

    print("Checking fonts…")
    download_fonts()

    if not args.no_download:
        print("Syncing images…")
        sync_images_from_gdrive(force=args.force_download)

    print("Reading YAML…")
    with open(YAML_PATH, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    sargas = {s['number']: s for s in data['sargas']}

    # ── Sarga-0 (front matter) ─────────────────────────────────────
    print("Parsing sarga-0…")
    s0_dir        = MD_BASE / 'sarga-0'
    s0_files      = sorted(s0_dir.glob('*.md'))
    s0_html_parts = []
    s0_entries    = []
    for sf in s0_files:
        sec_id, title, content = parse_sarga0_file(sf)
        if title != sf.stem:  # skip gallery/image-only files (no H1 heading)
            s0_entries.append((sec_id, title))
        # Files with no H1 title (e.g. image galleries) get a compact no-break wrapper
        inner = (f'<div class="s0-gallery">{content}</div>'
                 if title == sf.stem else content)
        s0_html_parts.append(f'<div class="front-matter-section">{inner}</div>')

    # ── Sargas ─────────────────────────────────────────────────────
    sarga_topic_ids   = {}
    sarga_topic_files = {}
    for n in vol_sargas:
        print(f"Parsing sarga-{n}…")
        sd  = MD_BASE / f'sarga-{n}'
        tfs = sorted(sd.glob('topic_*.md'))
        sarga_topic_files[n] = tfs
        ids = []
        for tf in tfs:
            num = int(re.search(r'topic_(\d+)', tf.stem).group(1))
            tid = f"s{n}-t{num:02d}"
            ids.append((tid, parse_topic(tf, sd, tid)['title']))
        sarga_topic_ids[n] = ids

    # ── TOC ────────────────────────────────────────────────────────
    print("Building TOC…")
    toc_html = build_toc(
        s0_entries,
        [(sargas[n], sarga_topic_ids[n]) for n in vol_sargas]
    )

    # ── Sarga HTML ─────────────────────────────────────────────────
    sarga_html_parts = []
    for n in vol_sargas:
        sd = MD_BASE / f'sarga-{n}'
        sarga_html_parts.append(
            build_sarga_html(sargas[n], sarga_topic_files[n], sd, f'sarga{n}-section',
                         compact_pratipa=compact_pratipa)
        )

    # ── Dynamic CSS (page size + @page rules) ─────────────────────
    dynamic_css = build_dynamic_css([sargas[n] for n in vol_sargas], page_size, margins)

    # ── Assemble HTML ──────────────────────────────────────────────
    cover_front = REPO_ROOT / 'images' / 'cover_front.png'
    cover_back  = REPO_ROOT / 'images' / 'cover_back.png'
    front_html  = (f'<div class="cover-pg">'
                   f'<img src="{cover_front.as_uri()}" alt="front cover">'
                   f'</div>') if cover_front.exists() else ''
    back_html   = (f'<div class="cover-pg">'
                   f'<img src="{cover_back.as_uri()}" alt="back cover">'
                   f'</div>') if cover_back.exists() else ''

    html = f"""<!DOCTYPE html>
<html lang="te">
<head>
  <meta charset="UTF-8">
  <title>గణపతి సంభవమ్ — {vol_label}</title>
  <style>{dynamic_css}</style>
</head>
<body>
{front_html}
{''.join(s0_html_parts)}
{toc_html}
{''.join(sarga_html_parts)}
{back_html}
<div class="footer-line-rule" aria-hidden="true"></div>
</body>
</html>"""

    # ── Write preview HTML ─────────────────────────────────────────
    OUTPUT_DIR.mkdir(exist_ok=True)
    preview_path.write_text(html, encoding='utf-8')
    print(f"Preview : {preview_path}")

    # ── Generate PDF ───────────────────────────────────────────────
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
