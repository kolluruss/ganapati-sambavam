# గణపతి సంభవము (Ganapati Sambavam)

A collaborative publishing project for **Ganapati Sambavam**, presented in Telugu with verse-by-verse commentary, meaning, resonance, and poetic translation.

Each verse is authored in Markdown, illustrated with AI-generated images, and automatically typeset into a PDF whenever content changes — with the final PDF published as a GitHub Release.

**[Download latest PDF](https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati-sambavam.pdf)**

---

## Table of Contents

- [Project Architecture](#project-architecture)
- [Repository Structure](#repository-structure)
- [How the Pipeline Works](#how-the-pipeline-works)
- [For Developers — Local Setup](#for-developers--local-setup)
- [For Content Editors — Updating Verses via GitHub](#for-content-editors--updating-verses-via-github)

---

## Project Architecture

```
Markdown files (markdown/v-*.md)
        │
        │  edit on GitHub or locally
        ▼
GitHub Actions (on push to main)
        │
        ├── Downloads images from Google Drive (read-only, API key)
        ├── Runs publishing/make_book.py
        │       │
        │       ├── Parses all verse markdown files
        │       ├── Builds styled HTML (Telugu fonts, colour-coded sections)
        │       └── Renders to PDF via WeasyPrint
        │
        └── Publishes PDF → GitHub Release (vMAJOR.MINOR.PATCH)
                   └── Every push creates a new versioned release
```

**Key design decisions:**
- Content lives in plain Markdown — no special software needed to edit it
- Images are stored in Google Drive (not in the repo) to keep repository size small
- PDF generation is fully automated — editors never touch the publishing scripts
- Every push creates a new versioned GitHub Release — full history is preserved

---

## Repository Structure

```
ganapati-sambavam/
├── markdown/               # One .md file per verse (v-1.md, v-2.md, …)
├── image_prompts/          # AI image prompts used to generate illustrations
├── publishing/
│   ├── make_book.py        # Builds the full PDF
│   ├── verse_to_pdf.py     # Builds a single-verse PDF (for previewing)
│   ├── book.css            # PDF styles for the full book (layout, fonts, colours)
│   ├── verse.css           # PDF styles for single-verse preview
│   ├── VERSION             # Semantic version — major.minor (patch is auto-computed)
│   ├── requirements.txt    # Python dependencies
│   ├── fonts_cache/        # Telugu fonts (Ponnala, Gidugu) committed to repo
│   └── gdrive_credentials.json   # OAuth2 app credentials — NOT committed (gitignored)
├── .github/
│   └── workflows/
│       └── generate-pdf.yml  # CI pipeline
├── images/                 # Downloaded from Google Drive at runtime — NOT committed
├── pdfs/                   # Generated PDF output — NOT committed
└── .gitignore
```

### Verse Markdown Format

Each file in `markdown/` follows this structure:

```markdown
## శ్లోకము - 1

### 1. మూల శ్లోకము
(Original Sanskrit verse)

### 2. అర్థము
(Telugu meaning / interpretation)

### 3. అనునాదము
(Sanskrit resonance / paraphrase)

### 4. అనువాదము
(Telugu poetic translation)
```

---

## How the Pipeline Works

1. A commit is pushed to `main` that includes changes to any file under `markdown/`
2. GitHub Actions triggers `.github/workflows/generate-pdf.yml`
3. The runner computes a semantic version (`vMAJOR.MINOR.PATCH`), generates the PDF, and publishes it as a new GitHub Release

The pipeline also has a **manual trigger** — go to the Actions tab on GitHub and click "Run workflow".

### Versioning

| Part | Source | When to change |
|---|---|---|
| MAJOR | `publishing/VERSION` file | Major restructuring, format overhaul |
| MINOR | `publishing/VERSION` file | New content sections, significant additions |
| PATCH | Auto-computed (total git commit count) | Every push — automatic |

### GitHub Secrets required

| Secret | Purpose | How to obtain |
|---|---|---|
| `GOOGLE_API_KEY` | Read images from Google Drive (read-only) | Google Cloud Console → Credentials → API Key |

Add at: `Settings → Secrets and variables → Actions → New repository secret`

---

## For Developers — Local Setup

### Prerequisites

- Python 3.9+
- `pip install -r publishing/requirements.txt`
- WeasyPrint system libraries

**macOS:**
```bash
brew install pango cairo libffi
```

**Ubuntu / Debian:**
```bash
sudo apt-get install -y \
  libpango-1.0-0 libpangoft2-1.0-0 \
  libcairo2 libgobject-2.0-0 \
  libharfbuzz0b libfribidi0
```

### Running locally

```bash
# Generate the full book (downloads images, saves PDF to pdfs/)
python3.9 publishing/make_book.py

# Skip image download (use whatever is cached in images/)
python3.9 publishing/make_book.py --no-download

# Force re-download of all images from Google Drive
python3.9 publishing/make_book.py --force-download

# Generate a single verse PDF for quick styling preview
python3.9 publishing/verse_to_pdf.py --verse markdown/v-1.md
```

### Modifying the PDF styling

Edit `publishing/book.css` (full book) or `publishing/verse.css` (single verse). Open the HTML preview in a browser to iterate instantly without regenerating the PDF:

```bash
python3.9 publishing/make_book.py --no-download
open pdfs/ganapati-sambavam-preview.html
```

### Google Drive setup

Set `GDRIVE_FOLDER_ID` in `publishing/make_book.py` to your images folder ID, and set `GOOGLE_API_KEY` in your shell. The folder must be shared as **"Anyone with the link can view"**.

---

## For Content Editors — Updating Verses via GitHub

You do **not** need to install anything. All editing happens on GitHub's website. The PDF regenerates automatically within a few minutes of saving.

**PDF download link (always the latest):**
```
https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati-sambavam.pdf
```

### Steps

1. Go to [github.com/kolluruss/ganapati-sambavam](https://github.com/kolluruss/ganapati-sambavam)
2. Click the **`markdown`** folder → find the verse file (e.g. `v-1.md`)
3. Click the **pencil icon** to open the editor
4. Edit the content lines — **do not change the headings** (`##` or `###` lines)
5. Scroll down → write a brief commit message → click **"Commit changes"**
6. Click the **Actions** tab to watch the pipeline — green checkmark means the PDF is updated

### Adding a new verse

1. In `markdown/`, click **"Add file" → "Create new file"**
2. Name it `v-N.md` (e.g. `v-5.md`)
3. Use this template:

```
## శ్లోకము - 5

### 1. మూల శ్లోకము

(paste the Sanskrit verse here)

### 2. అర్థము

(paste the Telugu meaning here)

### 3. అనునాదము

(paste the Sanskrit resonance here)

### 4. అనువాదము

(paste the Telugu poetic translation here)
```

4. Commit — the pipeline includes it automatically in the next build.
