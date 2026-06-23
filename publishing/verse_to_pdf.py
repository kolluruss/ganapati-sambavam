#!/usr/bin/env python3.9
"""
verse_to_pdf.py  —  Ganapati Sambavam: one verse markdown → styled PDF

HOW TO RUN
----------
  cd /path/to/ganapati-sambavam
  python3.9 publishing/verse_to_pdf.py

  Optional arguments:
    --verse         PATH   path to a specific verse .md file (default: markdown/v-1.md)
    --out           PATH   where to write the PDF            (default: pdfs/v-1.pdf)
    --html          PATH   where to write the HTML preview   (default: pdfs/v-1-preview.html)
    --upload-drive         also upload PDF to Google Drive after generating

  Example: run for verse 5
    python3.9 publishing/verse_to_pdf.py --verse markdown/v-5.md --out pdfs/v-5.pdf

MODIFYING THE LOOK
------------------
Edit publishing/verse.css — all visual decisions live there.
Open the HTML preview in a browser to iterate on styling without
re-running WeasyPrint each time.
"""

import re, sys, argparse
from pathlib import Path
from html import escape as esc


BASE                 = Path(__file__).resolve().parent.parent
CSS_FILE             = BASE / "publishing" / "verse.css"
GDRIVE_FOLDER_ID     = ""   # images source — set to your Drive folder ID
GDRIVE_PDF_FOLDER_ID = ""   # PDF destination (--upload-drive)
GDRIVE_CREDS_FILE    = BASE / "publishing" / "gdrive_credentials.json"
GDRIVE_TOKEN_FILE    = BASE / "publishing" / "gdrive_token.json"


# ── Google Drive image sync ───────────────────────────────────────

def sync_images_from_gdrive(force: bool = False):
    """Download all images from the Google Drive images folder into BASE/images/."""
    img_dir  = BASE / "images"
    existing = list(img_dir.glob("v-*.png"))
    if existing and not force:
        print(f"Images cached: {len(existing)} files in {img_dir}")
        return

    if not GDRIVE_FOLDER_ID:
        print("No GDRIVE_FOLDER_ID configured — skipping image download.")
        return

    img_dir.mkdir(exist_ok=True)
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
        dest = img_dir / f["name"]
        req  = service.files().get_media(fileId=f["id"])
        buf  = io.FileIO(dest, mode="wb")
        dl   = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        print(f"  {f['name']}")

    print(f"Downloaded {len(pngs)} images to {img_dir}")


_GOOGLE_PKG_IMPORTS = {
    "google-auth":              "google.auth",
    "google-auth-oauthlib":     "google_auth_oauthlib",
    "google-auth-httplib2":     "google_auth_httplib2",
    "google-api-python-client": "googleapiclient",
}

def _ensure_packages(*packages):
    import subprocess
    for pkg in packages:
        import_name = _GOOGLE_PKG_IMPORTS.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pkg}…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


def get_drive_reader():
    import os
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        _ensure_packages("google-api-python-client")
        from googleapiclient.discovery import build
        return build("drive", "v3", developerKey=api_key)
    return get_drive_service()


def get_drive_service():
    """Drive service for write operations (used by --upload-drive)."""
    import os
    _ensure_packages(
        "google-auth", "google-auth-oauthlib",
        "google-auth-httplib2", "google-api-python-client",
    )
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

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


# ── Parse verse markdown ─────────────────────────────────────────

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


def build_section_html(sec: dict) -> str:
    num   = sec["num"]
    verse = is_verse_section(sec["lines"])
    html  = f'<div class="section sec-{num}">\n'
    html += f'  <div class="sec-label">{esc(sec["label"])}</div>\n'
    if verse:
        html += '  <div class="verse-body">\n'
        for line in sec["lines"]:
            html += f'    <div class="verse-line">{esc(line)}</div>\n'
        html += '  </div>\n'
    else:
        html += '  <div class="prose-body">\n'
        for line in sec["lines"]:
            html += f'    <p class="prose-para">{esc(line)}</p>\n'
        html += '  </div>\n'
    html += '</div>\n'
    return html


def build_html(verse_data: dict, image_path=None) -> str:
    title = verse_data["title"]
    body  = f'<h1 class="verse-title">{esc(title)}</h1>\n'

    if image_path and image_path.exists():
        body += (
            f'<div class="verse-image">'
            f'<img src="{image_path}" alt="{esc(title)}">'
            f'</div>\n'
        )

    for sec in verse_data["sections"]:
        body += build_section_html(sec)

    return f"""<!DOCTYPE html>
<html lang="te">
<head>
  <meta charset="UTF-8">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="../publishing/verse.css">
</head>
<body>
{body}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Convert a verse .md to a styled PDF")
    parser.add_argument("--verse", default=str(BASE / "markdown" / "v-1.md"),
                        help="Path to verse markdown file")
    parser.add_argument("--out",   default="",
                        help="Output PDF path (default: pdfs/<verse-name>.pdf)")
    parser.add_argument("--html",  default="",
                        help="Output HTML preview path")
    parser.add_argument("--no-download", action="store_true",
                        help="Skip Google Drive image download")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-download images even if already cached")
    parser.add_argument("--upload-drive", action="store_true",
                        help="Also upload PDF to Google Drive after generating")
    args = parser.parse_args()

    if not args.no_download:
        sync_images_from_gdrive(force=args.force_download)

    verse_path = Path(args.verse)
    verse_name = verse_path.stem
    pdfs_dir   = BASE / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)

    out_pdf  = Path(args.out)  if args.out  else pdfs_dir / f"{verse_name}.pdf"
    out_html = Path(args.html) if args.html else pdfs_dir / f"{verse_name}-preview.html"

    image_path = BASE / "images" / f"{verse_name}.png"

    print(f"Parsing  : {verse_path}")
    data = parse_verse(verse_path)
    print(f"  Title  : {data['title']}")
    print(f"  Sections: {[s['label'] for s in data['sections']]}")

    html = build_html(data, image_path)

    out_html.write_text(html, encoding="utf-8")
    print(f"  Preview : {out_html}")
    print(f"  TIP: open the preview in your browser to iterate on styling.")

    print("Generating PDF…")
    from weasyprint import HTML as WP, CSS
    out_pdf.parent.mkdir(exist_ok=True)
    stylesheet = CSS(filename=str(CSS_FILE))
    WP(string=html, base_url=str(BASE)).write_pdf(str(out_pdf), stylesheets=[stylesheet])
    size_kb = out_pdf.stat().st_size // 1024
    print(f"  Done    : {out_pdf}  ({size_kb} KB)")

    print(f"Saved locally: {out_pdf}")
    if args.upload_drive:
        print("Uploading to Google Drive…")
        upload_pdf_to_gdrive(out_pdf)


if __name__ == "__main__":
    main()
