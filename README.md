# గణపతి సంభవమ్ (Ganapati Sambhavam)

A Telugu translation and scholarly commentary of the Sanskrit Mahakavya **గణపతి సంభవమ్**, originally composed by **Mahamahopadhyaya Vidya-Vachaspati Pandit Prabhudatta Shastri** (1892–1979) and published in 1968 by Archana Prakashan, Nagpur.

**Translator:** Kolluru Seetarama Sarma

Content is authored in Markdown, illustrated with AI-generated images, and automatically typeset into a PDF whenever content changes — with the final PDF published as a GitHub Release.

**[Download latest PDF](https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati-sambavam.pdf)**

Also available — the English/Devanagari edition, and an **Easy Read** edition of it that puts the shloka (Devanagari + IAST) and its English meaning on odd (right-hand) pages, with the Anvaya and word-by-word Meaning of Terms on the facing even (left-hand) pages, so you can read straight through and glance at the grammatical detail only when you want it:

- **[Download English/Devanagari PDF](https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati_sambhavam_english.pdf)**
- **[Download English/Devanagari PDF — Easy Read edition](https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati_sambhavam_english_easyread.pdf)**

---

## Table of Contents

- [About the Work](#about-the-work)
- [Book Organization](#book-organization)
- [Repository Structure](#repository-structure)
- [Content File Format](#content-file-format)
- [Sarga Overview](#sarga-overview)
- [About the Original Poet](#about-the-original-poet)
- [About the Translator](#about-the-translator)
- [Project Architecture](#project-architecture)
- [For Developers — Local Setup](#for-developers--local-setup)
- [For Content Editors — Updating Content via GitHub](#for-content-editors--updating-content-via-github)

---

## About the Work

*Ganapati Sambhavam* is a 10-sarga Sanskrit Mahakavya written in classical meters following traditional Gana rules. Inspired by Kalidasa's *Kumarasambhavam*, it narrates the birth and life of Ganesha — from the wedding of Shiva and Parvati, through Ganesha's creation, beheading, and resurrection with an elephant head, to his role as scribe of the Mahabharata and his appointment as lord of the Ganas.

What makes this modern epic distinctive is its weaving of contemporary themes — democracy, gender equality, nationalism, and social justice — into classical Sanskrit verse. The 9th sarga, which compares Ganesha's form to an ideal democratic ruler, is considered one of the most revolutionary passages in modern Sanskrit literature.

---

## Book Organization

The book is organized into three levels:

| Level | Term | Description |
|---|---|---|
| Chapter | Sarga (సర్గ) | 10 chapters, each narrating a major episode |
| Section | Topic (విభాగం) | Logical grouping of related verses within a sarga |
| Unit | Shloka (శ్లోకము) | Individual Sanskrit verse with full Telugu commentary |

**Language plan:** Telugu is the first published language. Additional languages are planned for future releases. The `markdown/` folder is structured by language (`markdown/telugu/`) to support this.

---

## Repository Structure

```
ganapati-sambavam/
├── markdown/
│   └── telugu/                    # Telugu translation (first language)
│       ├── meta_data/
│       │   ├── chapter_topics.yaml        # Structured sarga/topic/shloka-range data
│       │   ├── chapter_topics.md          # Narrative overview of all 10 sargas
│       │   └── summary_by_chpaters.md     # Chapter-by-chapter summaries
│       │
│       ├── research/
│       │   ├── author_and_book_google.md  # Bibliographic research on the author
│       │   ├── critical_study_reasearch_paper.md
│       │   ├── book_prompt.md             # Working prompts used in translation
│       │   ├── prompt.txt
│       │   └── visual_prompts.md          # Image generation prompts
│       │
│       ├── sarga-0/                       # Front matter (in reading order)
│       │   ├── 01_mumdumata.md            # Translator's foreword (ముందుమాట)
│       │   ├── 02_kavi_parichayamu.md     # Poet biography (కవి పరిచయము)
│       │   ├── 03_kavya_parichayamu.md    # Introduction to the epic (కావ్య పరిచయము)
│       │   ├── 04_tulanatmaka_sameeksha.md# Comparative review with Kumarasambhavam
│       │   ├── 05_samarpana.md            # Original Sanskrit dedication (సమర్పణ)
│       │   ├── 06_peethika.md             # Author's preface (పీఠిక)
│       │   └── 07_abhiprayamu.md          # Publishers' note (అభిప్రాయము)
│       │
│       ├── sarga-1/    # హిమగిరి పరిచయము        (98 shlokas, 10 topics)
│       ├── sarga-2/    # గిరిశ గిరిజా పాణిగ్రహణము (78 shlokas, 10 topics)
│       ├── sarga-3/    # యోగశక్తి చమత్కృతి       (96 shlokas, 8 topics)
│       ├── sarga-4/    # శాస్త్రార్థ శస్త్రీభావము  (89 shlokas, 7 topics)
│       ├── sarga-5/    # గజమనుజ యోజనోత్సవము    (78 shlokas, 7 topics)
│       ├── sarga-6/    # తానైకదంత ప్రసంగము      (88 shlokas, 8 topics)
│       ├── sarga-7/    # మహాభారత లేఖాఖ్యానము   (94 shlokas, 7 topics)
│       ├── sarga-8/    # దేవమోదకోపహార గ్రహము   (73 shlokas, 8 topics)
│       ├── sarga-9/    # గణశాసనోత్కర్షము        (66 shlokas, 9 topics)
│       └── sarga-10/   # కావ్యాంతర పుష్పార్పణము  (90 shlokas, 10 topics)
│
├── image_prompts/          # AI image prompts used to generate illustrations
├── images/                 # Illustration images (committed to repo)
├── publishing/
│   ├── make_book.py        # Builds the full PDF
│   ├── make_pdf_book.py    # Alternative PDF builder
│   ├── verse_to_pdf.py     # Builds a single-verse PDF (for previewing)
│   ├── book.css            # PDF styles (layout, fonts, colours)
│   ├── verse.css           # PDF styles for single-verse preview
│   ├── VERSION             # Semantic version — major.minor (patch is auto-computed)
│   ├── requirements.txt    # Python dependencies
│   └── fonts_cache/        # Telugu fonts (Ponnala, Gidugu) committed to repo
├── .github/
│   └── workflows/
│       └── generate-pdf.yml  # CI pipeline
└── .gitignore
```

**Total:** 10 sargas · ~847 shlokas · organized into topics within each sarga

---

## Content File Format

Each sarga folder contains topic files (`topic_01.md`, `topic_02.md`, …). Each topic file covers all shlokas for that section. Every shloka follows this five-part structure:

| Section | Telugu | Content |
|---|---|---|
| Verse | (bold text) | Original Sanskrit shloka with verse number |
| పదచ్ఛేదము | Word-splitting | Sandhi resolved into individual words |
| అన్వయము | Prose order | Words rearranged into natural Sanskrit sentence order |
| ప్రతిపదార్థము | Word-by-word | Meaning of each word with samasa analysis |
| భావము | Meaning | Summary in Telugu prose |

---

## Sarga Overview

| Sarga | Telugu Title | Shloka Range | Theme |
|---|---|---|---|
| 1 | హిమగిరి పరిచయము | 1–98 | Himalayas, Kashmir, Nepal — geographical panorama |
| 2 | గిరిశ గిరిజా పాణిగ్రహణము | 1–78 | Wedding of Shiva and Parvati |
| 3 | యోగశక్తి చమత్కృతి | 1–96 | Parvati creates Ganesha from clay using yogic power |
| 4 | శాస్త్రార్థ శస్త్రీభావము | 1–89 | Debate between Shiva and the boy; beheading |
| 5 | గజమనుజ యోజనోత్సవము | 1–78 | Elephant head transplant; Ganesha's childhood |
| 6 | తానైకదంత ప్రసంగము | 1–88 | Confrontation with Parashurama; loss of one tusk |
| 7 | మహాభారత లేఖాఖ్యానము | 1–94 | Ganesha as scribe of the Mahabharata for Vyasa |
| 8 | దేవమోదకోపహార గ్రహము | 1–73 | The divine modaka; circumambulation of parents |
| 9 | గణశాసనోత్కర్షము | 1–66 | Ganesha's form as metaphor for democratic governance |
| 10 | కావ్యాంతర పుష్పార్పణము | 1–90 | Poet's autobiography and other works |

Detailed topic breakdowns (section titles and shloka ranges) are in [`markdown/telugu/meta_data/chapter_topics.yaml`](markdown/telugu/meta_data/chapter_topics.yaml).

---

## About the Original Poet

**Pandit Prabhudatta Shastri** (1892–1979) was born in Tatarpur village, Alwar district, Rajasthan, into the scholarly Mishra lineage. Orphaned at two, he was raised by his mother and grandfather and educated in Mandawa under traditional Sanskrit teachers. He later taught in Delhi, where he won the gold medal at the Kurukshetra Gita competition and was honored as *Sarvottama Kavi* at the All-India Sanskrit Literary Conference in Patna.

His other Sanskrit works include *Bhagavad Gita Vyangya Mandakini*, *Jhansi Shauryamritam*, *Rashtradhwajamritam*, and *Gandhi Nandi Shraddhamamritam* — notable for integrating Indian nationalist themes into classical Sanskrit meters.

---

## About the Translator

**Kolluru Seetarama Sarma** undertook this translation to bring this rare Mahakavya to Telugu readers, inspired by his father Brahmasri Kolluru Avatara Sarma, a noted Sanskrit scholar and Ganesha devotee. The source manuscript was obtained from the University of Illinois library with the help of Sri Palli Venkatasarma.

---

## Project Architecture

```
Markdown files (markdown/telugu/sarga-N/topic_NN.md)
        │
        │  edit on GitHub or locally
        ▼
GitHub Actions (on push to main)
        │
        ├── Runs publishing/make_book.py
        │       │
        │       ├── Parses all topic markdown files in sarga order
        │       ├── Builds styled HTML (Telugu fonts, colour-coded sections)
        │       └── Renders to PDF via WeasyPrint
        │
        └── Publishes PDF → GitHub Release (vMAJOR.MINOR.PATCH)
                   └── Every push creates a new versioned release
```

**Key design decisions:**
- Content lives in plain Markdown — no special software needed to edit
- Organized by language → sarga → topic, ready for additional languages
- PDF generation is fully automated — editors never touch the publishing scripts
- Every push creates a new versioned GitHub Release — full history is preserved

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
# Generate the full book PDF
python3.9 publishing/make_book.py

# Generate a single-verse PDF for quick styling preview
python3.9 publishing/verse_to_pdf.py --verse markdown/telugu/sarga-1/topic_01.md
```

### Modifying the PDF styling

Edit `publishing/book.css`. Open the HTML preview in a browser to iterate without regenerating the full PDF:

```bash
python3.9 publishing/make_book.py --no-download
open pdfs/ganapati-sambavam-preview.html
```

---

## For Content Editors — Updating Content via GitHub

You do **not** need to install anything. All editing happens on GitHub's website. The PDF regenerates automatically within a few minutes of saving.

**PDF download link (always the latest):**
```
https://github.com/kolluruss/ganapati-sambavam/releases/latest/download/ganapati-sambavam.pdf
```

### Editing an existing topic file

1. Go to [github.com/kolluruss/ganapati-sambavam](https://github.com/kolluruss/ganapati-sambavam)
2. Navigate to `markdown/telugu/sarga-N/` → open the topic file (e.g. `topic_01.md`)
3. Click the **pencil icon** to open the editor
4. Edit the content — **do not change section headings**
5. Scroll down → write a brief commit message → click **"Commit changes"**
6. Click the **Actions** tab to watch the pipeline — green checkmark means the PDF is updated

### Adding a new topic file

1. In the appropriate `markdown/telugu/sarga-N/` folder, click **"Add file" → "Create new file"**
2. Name it `topic_NN.md` (e.g. `topic_11.md`)
3. Follow the five-section format for each shloka (see [Content File Format](#content-file-format) above)
4. Commit — the pipeline includes it automatically in the next build
