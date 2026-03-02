# PDF Text Replacement Pipeline

## Overview

This project provides a round-trip PDF transformation pipeline that converts born-digital PDFs to HTML, optionally translates or modifies text content, and renders the result back to PDF while preserving the original page dimensions.

**Workflows:**
- **JSON Mapping:** `PDF → HTML → [JSON Text Replacement] → PDF`
- **LLM Translation:** `PDF → HTML → [LLM Translation] → PDF`

---

## Architecture

```
┌─────────────┐     pdftohtml      ┌─────────────┐
│  Input PDF  │ ─────────────────> │    HTML     │
└─────────────┘                    └──────┬──────┘
       │                                  │
       │ PyMuPDF                          │ BeautifulSoup
       │ (get dimensions)                 │ (text replacement)
       │                                  │
       v                                  v
┌─────────────┐                    ┌─────────────┐
│  PageSize   │                    │ Modified    │
│  (points)   │                    │ HTML        │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │                                  │ Playwright
       │                                  │ (Chromium)
       │                                  │
       v                                  v
┌─────────────┐                    ┌─────────────┐
│  Output     │ <───────────────── │  Rendered   │
│  PDF        │    (dimensions)    │  PDF        │
└─────────────┘                    └─────────────┘
```

---

## Environment Configuration

Create a `.env` file for LLM configuration:

```bash
# LLM API Configuration (OpenAI-compatible)
LLM_API_URL=http://localhost:8000/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=Qwen3-235B-A22B

# Optional settings
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.1
LLM_BATCH_SIZE=20
```

## Components

### 1. Entry Point (`cli.py`)

The command-line interface orchestrates the entire pipeline.

**Arguments:**
- `--pdf-in`: Source PDF path (required)
- `--workdir`: Working directory for intermediate HTML files (required)
- `--mapping-json`: Optional JSON file with text replacements `{ "original": "replacement" }`
- `--pdf-out`: Output PDF path (required)

**Flow:**
1. Validate input paths
2. Extract page dimensions from source PDF
3. Convert PDF → HTML
4. Apply text replacements (if mapping provided)
5. Render HTML → PDF with preserved dimensions

---

### 2. PDF to HTML Conversion (`convert_pdf_to_html.py`)

Uses Poppler's `pdftohtml` tool to convert PDF to HTML.

**Flags used:**
- `-c`: Complex output (preserves layout/positioning)
- `-s`: Single HTML file (not frameset)
- `-noframes`: No frames output

**Output:** Single HTML file with CSS-based absolute positioning that mirrors the PDF layout.

---

### 3. Text Replacement (`replace_html_text.py`)

Uses BeautifulSoup to traverse and modify text nodes in the HTML.

**Key behaviors:**
- Only replaces **exact** matches (after `strip()`)
- Preserves leading/trailing whitespace to maintain layout
- Returns statistics (`replaced`, `skipped` counts)

**Limitations:**
- Requires exact string matches (whitespace-sensitive after stripping)
- Cannot handle text split across multiple DOM nodes
- Does not handle HTML entities (`&amp;` vs `&`)

---

### 4. LLM Translation (`translator_llm.py`)

**NEW:** Text-node level translation using OpenAI-compatible LLM APIs.

**Key Features:**
- **Text-node extraction:** Extracts individual text nodes (NavigableString) from HTML
- **Auto language detection:** Detects source language from content samples
- **Smart batching:** Processes multiple nodes per API call (configurable batch size)
- **Preserves ALL structure:** Maintains HTML/CSS positioning, images, styling, nested elements
- **Robust prompting:** Comprehensive system prompt with formatting rules

**Translation Strategy:**
1. Extract all text nodes from HTML (leaf text content)
2. Filter out non-translatable content (numbers, whitespace, HTML entities)
3. Detect source language (if not provided)
4. Translate in batches via LLM API
5. Replace each text node individually using `node.replace_with()` - this preserves all surrounding HTML

**Why Text-Node Level?**
- **Element-level failed:** Replacing entire elements destroyed nested structure
- **Block-level failed:** Replacing container divs wiped out all child elements
- **Text-node level:** Only replaces the text content, leaving all HTML markup intact

**Prompt Design:**
- **System prompt:** Strict rules for preserving numbers, emails, codes, acronyms
- **Output format:** JSON mapping `node_id -> translated_text`
- **Node independence:** Each text snippet translated independently

### 5. PDF Page Size Extraction (`pdf_page_size.py`)

Uses PyMuPDF (`fitz`) to read the MediaBox dimensions of the first page.

**Returns:** `PageSize(width_pt, height_pt)` — dimensions in points (1 inch = 72 pt)

---

### 6. HTML to PDF Rendering (`render_html_to_pdf.py`)

Uses Playwright with headless Chromium to render HTML back to PDF.

**Fixes Applied:**
- **Removed `prefer_css_page_size`:** Was conflicting with explicit dimensions, causing wrong page size
- **CSS injection:** Sets white background (overrides pdftohtml's gray `#A0A0A0`)
- **Automatic scaling:** Calculates scale factor to fit pdftohtml's pixel-based content (usually 892px) into PDF points (595pt for A4)
- **Zero margins:** Preserves absolute positioning from pdftohtml

**Scaling Logic:**
```
Content size: 892px x 1262px (from pdftohtml)
PDF size: 595.3pt x 841.9pt (72 DPI)
Scale factor: 0.667 (content * scale = PDF dimensions)
```

---

### 7. Direct PDF Translation (`translate_pdf_direct.py`)

Direct mode rewrites text lines on the original PDF coordinates (without `pdftohtml`), preserving page visuals more robustly for many documents.

---

## Data Flow

### With JSON Mapping:
```
Input PDF
    │
    ├──[PyMuPDF]──> PageSize (width_pt, height_pt)
    │
    ├──[pdftohtml]──> HTML (layout-preserved)
    │       │
    │       ├──[BeautifulSoup + JSON mapping]──> Modified HTML
    │       │                                    (if --mapping-json)
    │       └──[or unchanged]──────────────────> Original HTML
    │
    └──[Playwright/Chromium + PageSize]──> Output PDF
```

### With LLM Translation (HTML Engine):
```
Input PDF
    │
    ├──[PyMuPDF]──> PageSize (width_pt, height_pt)
    │
    ├──[pdftohtml]──> HTML (layout-preserved) ──> (optional: --save-html) ──> output/html/
    │       │
    │       ├──[Extract Text Nodes]──> Text Nodes (NavigableString)
    │       │                         │
    │       │                         ├──[Detect Language]
    │       │                         │
    │       │                         └──[LLM Translate]──> Translations
    │       │                                              (batched API calls)
    │       │
    │       └──[Replace Text Nodes]──> Translated HTML (ALL structure preserved)
    │
    └──[Playwright/Chromium + PageSize]──> Output PDF
```

### With LLM Translation (Direct Engine):
```
Input PDF
    │
    ├──[PyMuPDF extract lines + bbox]──> Line records
    │
    ├──[LLM translate per line]──> Translated lines
    │
    ├──[Text-only redaction on original bbox]──> Remove source glyphs
    │
    └──[PyMuPDF insert_textbox]──> Output PDF (original layout preserved)
```

---

## Dependencies

| Tool/Library | Purpose | Installation |
|--------------|---------|--------------|
| `pdftohtml` | PDF → HTML conversion | Poppler utils (`apt install poppler-utils` or equivalent) |
| `PyMuPDF` (`fitz`) | PDF page size extraction | `pip install pymupdf` |
| `BeautifulSoup4` (`bs4`) | HTML parsing/modification | `pip install beautifulsoup4` |
| `lxml` | HTML parser backend | `pip install lxml` |
| `Playwright` | HTML → PDF rendering | `pip install playwright && playwright install chromium` |
| `openai` | LLM API client | `pip install openai` |
| `python-dotenv` | Environment variable loading | `pip install python-dotenv` |

---

## Usage

### Basic round-trip (no modifications):
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --pdf-out output.pdf
```

### With JSON text replacement:
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --mapping-json replacements.json \
  --pdf-out output.pdf
```

**Example `replacements.json`:**
```json
{
  "Hello World": "Bonjour le Monde",
  "Summary": "Résumé"
}
```

### With LLM Translation (NEW):
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --target-lang es \
  --pdf-out output.pdf
```

**With intermediate HTML files saved:**
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --target-lang es \
  --pdf-out output.pdf \
  --save-html
```

**Optional:** Specify source language (auto-detected if omitted):
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --source-lang en \
  --target-lang es \
  --pdf-out output.pdf
```

---

## Translation Notes

### Text-Node Level Translation

The LLM translator uses **text-node level translation** - the most granular approach:

**How it works:**
1. Extract all `NavigableString` nodes (leaf text) from the HTML
2. Translate each text snippet independently
3. Replace each node using `node.replace_with(new_text)`

**Why this works:**
- `replace_with()` only changes that specific text node
- All surrounding HTML structure is preserved exactly
- Parent elements (`<p>`, `<div>`), attributes, CSS positioning all remain intact
- Nested elements (`<b>`, `<i>`) are preserved

### Previous Failures

| Approach | Problem |
|----------|---------|
| **Block-level** (container divs) | `div.string = text` destroyed all child elements (`<p>`, `<img>`, etc.) |
| **Element-level** (`<p>`, `<b>`) | Still destroyed nested structure within elements |
| **Text-node level** (current) | ✅ Only replaces the text, preserves everything else |

### Language Detection
- Uses LLM to analyze text samples from the document
- Returns ISO 639-1 language codes (en, es, fr, de, etc.)
- Can be overridden with `--source-lang` if detection is incorrect

### Cost Optimization
- **Batching:** Multiple nodes per API call (default: 50)
- **Filtering:** Skips pure numbers, whitespace, HTML entities, and very short strings

## Known Limitations & Issues

### 1. Page Size Handling
The `render_html_to_pdf.py` module sets:
- `prefer_css_page_size=False`
- Explicit `width`/`height` parameters

If the HTML contains `@page` CSS rules, Chromium may prioritize them over the explicit dimensions, causing page size mismatch.

### 2. Text Replacement Fragility
The current implementation requires exact string matches. It will fail if:
- Text spans multiple HTML elements
- Whitespace differs between mapping keys and HTML content
- HTML entities are used (`&amp;` vs `&`)
- Punctuation or capitalization differs

### 3. Layout Dependencies
- Relies on `pdftohtml`'s CSS positioning — complex PDFs may not render identically
- Absolute positioning can break if fonts are not available on the rendering system

### 4. Single Page Size
Only extracts dimensions from the first page — multi-page PDFs with varying page sizes will have all pages rendered at the first page's dimensions.

---

## Future Enhancements

| Feature | Description |
|---------|-------------|
| Element-ID-based replacement | Replace by `id` or coordinates instead of text matching |
| Multi-page size support | Handle varying page dimensions within a single PDF |
| Post-processing | Add dedicated PDF post-processing module for metadata preservation, PDF/A compliance |
| Font embedding | Ensure fonts are embedded or substituted correctly |
| Batch processing | Process multiple PDFs in parallel |
| OCR integration | Handle scanned/image-based PDFs |

---

## File Structure

```
doc_generator/
├── cli.py                      # Entry point & orchestration
├── convert_pdf_to_html.py      # PDF → HTML (Poppler)
├── replace_html_text.py        # HTML text modification via JSON (BeautifulSoup)
├── translator_llm.py           # HTML translation via LLM (NEW)
├── translate_pdf_direct.py     # Direct PDF line translation (PyMuPDF + LLM)
├── render_html_to_pdf.py       # HTML → PDF (Playwright)
├── pdf_page_size.py            # PDF dimension extraction (PyMuPDF)
├── app/                        # Modular FastAPI application (entrypoint: app.main:app)
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration (not committed)
├── .gitignore                  # Git ignore rules
├── ARCHITECTURE.md             # This document
└── ...                         # Sample PDFs, etc.
```
