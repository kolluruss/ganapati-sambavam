#!/usr/bin/env python3.9
"""
make_book.py  —  Ganapati Sambavam: all verses → single PDF

HOW TO RUN
----------
  cd /path/to/ganapati-sambavam
  python3.9 publishing/make_book.py                   # downloads images, generates PDF
  python3.9 publishing/make_book.py --no-download     # skip image download, use cached
  python3.9 publishing/make_book.py --force-download  # re-download all images
  python3.9 publishing/make_book.py --upload-drive    # also upload PDF to Google Drive

OUTPUT
------
  pdfs/ganapati-sambavam.pdf

In CI, the PDF is published as a GitHub Release asset by the workflow.
"""

import re
from pathlib import Path
from html import escape as esc

BASE                 = Path(__file__).resolve().parent.parent
MD_DIR               = BASE / "markdown"
IMG_DIR              = BASE / "images"
OUTPUT               = BASE / "pdfs" / "ganapati-sambavam.pdf"
PREVIEW              = BASE / "pdfs" / "ganapati-sambavam-preview.html"
CSS_FILE             = BASE / "publishing" / "book.css"
GDRIVE_FOLDER_ID     = ""   # images source — set to your Drive folder ID
GDRIVE_PDF_FOLDER_ID = ""   # PDF destination (--upload-drive)
GDRIVE_CREDS_FILE    = BASE / "publishing" / "gdrive_credentials.json"
GDRIVE_TOKEN_FILE    = BASE / "publishing" / "gdrive_token.json"


# ── Google Drive image sync ───────────────────────────────────────

def sync_images_from_gdrive(force: bool = False):
    """Download all images from the Google Drive images folder into IMG_DIR.

    Requires GOOGLE_API_KEY env var and the folder shared as 'Anyone with the link'.
    Uses Drive API pagination — no file-count limit.
    """
    existing = list(IMG_DIR.glob("v-*.png"))
    if existing and not force:
        print(f"Images cached: {len(existing)} files in {IMG_DIR}")
        return

    if not GDRIVE_FOLDER_ID:
        print("No GDRIVE_FOLDER_ID configured — skipping image download.")
        return

    IMG_DIR.mkdir(exist_ok=True)
    print(f"Downloading images from Google Drive folder {GDRIVE_FOLDER_ID}…")

    service = get_drive_reader()
    from googleapiclient.http import MediaIoBaseDownload
    import io

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
    print(f"Found {len(pngs)} images in Drive folder")

    for f in pngs:
        dest = IMG_DIR / f["name"]
        req  = service.files().get_media(fileId=f["id"])
        buf  = io.FileIO(dest, mode="wb")
        dl   = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        print(f"  {f['name']}")

    print(f"Downloaded {len(pngs)} images to {IMG_DIR}")


# ── Google Drive helpers ──────────────────────────────────────────

_GOOGLE_PKG_IMPORTS = {
    "google-auth":              "google.auth",
    "google-auth-oauthlib":     "google_auth_oauthlib",
    "google-auth-httplib2":     "google_auth_httplib2",
    "google-api-python-client": "googleapiclient",
}

def _ensure_packages(*packages):
    import subprocess, sys
    for pkg in packages:
        import_name = _GOOGLE_PKG_IMPORTS.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pkg}…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


def get_drive_reader():
    """Drive service for read-only operations (listing + downloading images).

    Uses GOOGLE_API_KEY env var when set — requires the images Drive folder
    to be shared as 'Anyone with the link'.
    Falls back to the write-capable service if the key is absent.
    """
    import os
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        _ensure_packages("google-api-python-client")
        from googleapiclient.discovery import build
        return build("drive", "v3", developerKey=api_key)
    return get_drive_service()


def get_drive_service():
    """Drive service for write operations (used by --upload-drive).

    Checks credentials in this order:
      1. GDRIVE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET env vars
      2. Local OAuth2 browser flow (needs publishing/gdrive_credentials.json)
    """
    import os
    _ensure_packages(
        "google-auth", "google-auth-oauthlib",
        "google-auth-httplib2", "google-api-python-client",
    )
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    # ── Option 1: refresh token ────────────────────────────────────
    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    client_id     = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        creds.refresh(Request())
        return build("drive", "v3", credentials=creds)

    # ── Option 2: local OAuth2 browser flow ────────────────────────
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = ["https://www.googleapis.com/auth/drive"]
    creds  = None

    if GDRIVE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GDRIVE_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GDRIVE_CREDS_FILE.exists():
                raise FileNotFoundError(
                    "\nNo Drive credentials found. Either:\n"
                    "  Set GDRIVE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET\n"
                    "  Or place OAuth2 Desktop credentials at publishing/gdrive_credentials.json\n"
                )
            flow  = InstalledAppFlow.from_client_secrets_file(str(GDRIVE_CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        GDRIVE_TOKEN_FILE.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


def upload_pdf_to_gdrive(pdf_path: Path) -> str:
    """Upload (or update) a PDF in the Shared Drive PDF folder. Returns the file URL."""
    from googleapiclient.http import MediaFileUpload

    service = get_drive_service()
    media   = MediaFileUpload(str(pdf_path), mimetype="application/pdf", resumable=True)

    existing = service.files().list(
        q=(f"name='{pdf_path.name}' and '{GDRIVE_PDF_FOLDER_ID}' in parents"
           " and trashed=false"),
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute().get("files", [])

    if existing:
        file_id = existing[0]["id"]
        service.files().update(
            fileId=file_id, media_body=media, supportsAllDrives=True
        ).execute()
        print(f"  Updated in Drive : {pdf_path.name}")
    else:
        meta   = {"name": pdf_path.name, "parents": [GDRIVE_PDF_FOLDER_ID]}
        result = service.files().create(
            body=meta, media_body=media, fields="id", supportsAllDrives=True
        ).execute()
        file_id = result["id"]
        print(f"  Uploaded to Drive: {pdf_path.name}")

    url = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"  URL: {url}")
    return url


# ── Helpers ──────────────────────────────────────────────────────

def verse_num(path: Path) -> int:
    """Extract primary verse number from filename: v-11.md → 11, v-7-1.md → 7."""
    m = re.search(r'v-(\d+)', path.stem)
    return int(m.group(1)) if m else 0


def find_image(num: int):
    """Return first available image path for verse N, or None."""
    for candidate in [f"v-{num}.png", f"v-{num}-1.png"]:
        p = IMG_DIR / candidate
        if p.exists():
            return p
    return None


# ── Parse one verse markdown ─────────────────────────────────────

def parse_verse(path: Path) -> dict:
    text   = path.read_text(encoding="utf-8")
    result = {"title": "", "sections": []}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            result["title"] = s[3:].strip()
            continue
        m = re.match(r"^#{2,4}\s+(\d+)\.\s+(.+)$", s)
        if m:
            result["sections"].append({
                "num":   int(m.group(1)),
                "label": m.group(2).strip(),
                "lines": [],
            })
            continue
        if result["sections"] and s:
            result["sections"][-1]["lines"].append(s)
    return result


def is_verse_section(lines: list) -> bool:
    if not lines:
        return False
    markers = sum(1 for l in lines if re.search(r"[|॥।]", l) or len(l) < 80)
    return markers / len(lines) >= 0.5


# ── Render one section ───────────────────────────────────────────

def section_html(sec: dict) -> str:
    num   = sec["num"]
    verse = is_verse_section(sec["lines"])
    parts = [f'<div class="section sec-{num}">',
             f'  <div class="sec-label">{esc(sec["label"])}</div>']
    if verse:
        parts.append('  <div class="verse-body">')
        for line in sec["lines"]:
            parts.append(f'    <div class="verse-line">{esc(line)}</div>')
        parts.append('  </div>')
    else:
        parts.append('  <div class="prose-body">')
        for line in sec["lines"]:
            parts.append(f'    <p class="prose-para">{esc(line)}</p>')
        parts.append('  </div>')
    parts.append('</div>')
    return "\n".join(parts)


# ── Build HTML for one verse (two pages) ─────────────────────────
#
#  Page 1: title + image (if any) + section 1 (shloka)
#  Page 2: title + sections 2, 3, 4

def verse_html(data: dict, img_path, verse_num_val: int) -> str:
    title    = esc(data["title"] or f"శ్లోకము - {verse_num_val}")
    sections = data["sections"]

    p1_cls = "verse-page first-verse-page" if verse_num_val == 1 else "verse-page"

    img_html = ""
    if img_path:
        img_html = (
            f'<div class="verse-image">'
            f'<img src="{img_path}" alt="{title}">'
            f'</div>'
        )

    sec1_html = section_html(sections[0]) if sections else ""

    page1 = (
        f'<div class="{p1_cls}" id="v{verse_num_val}">\n'
        f'  <h2 class="verse-title">{title}</h2>\n'
        f'  {img_html}\n'
        f'  {sec1_html}\n'
        f'</div>\n'
    )

    rest_html = "\n".join(section_html(s) for s in sections[1:])

    page2 = (
        f'<div class="verse-page">\n'
        f'  <h2 class="verse-title">{title}</h2>\n'
        f'  {rest_html}\n'
        f'</div>\n'
    )

    return page1 + page2


# ── Main ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Ganapati Sambavam PDF")
    parser.add_argument("--no-download", action="store_true",
                        help="Skip Google Drive image download (use local images only)")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-download images even if already cached")
    parser.add_argument("--upload-drive", action="store_true",
                        help="Upload generated PDF to Google Drive (default: local only)")
    args = parser.parse_args()

    if not args.no_download:
        sync_images_from_gdrive(force=args.force_download)

    md_files = sorted(MD_DIR.glob("v-*.md"), key=verse_num)
    print(f"Found {len(md_files)} verse files")

    verse_list = []
    for mdf in md_files:
        num  = verse_num(mdf)
        data = parse_verse(mdf)
        verse_list.append((num, data))

    bodies    = []
    img_count = 0
    for num, data in verse_list:
        img = find_image(num)
        if img:
            img_count += 1
        bodies.append(verse_html(data, img, num))
        print(f"  v-{num:3d}  {'[img]' if img else '     '}")

    print(f"\n{len(verse_list)} verses, {img_count} with images")

    html = f"""<!DOCTYPE html>
<html lang="te">
<head>
  <meta charset="UTF-8">
  <title>గణపతి సంభవము</title>
  <link rel="stylesheet" href="../publishing/book.css">
</head>
<body>
{''.join(bodies)}
</body>
</html>"""

    PREVIEW.parent.mkdir(exist_ok=True)
    PREVIEW.write_text(html, encoding="utf-8")
    print(f"Preview  : {PREVIEW}")

    print("Generating PDF…")
    from weasyprint import HTML as WP, CSS
    OUTPUT.parent.mkdir(exist_ok=True)
    stylesheet = CSS(filename=str(CSS_FILE))
    WP(string=html, base_url=str(BASE)).write_pdf(str(OUTPUT), stylesheets=[stylesheet])
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"Done     : {OUTPUT}  ({size_mb:.1f} MB)")

    print(f"Saved locally: {OUTPUT}")
    if args.upload_drive:
        print("Uploading to Google Drive…")
        upload_pdf_to_gdrive(OUTPUT)


if __name__ == "__main__":
    main()
