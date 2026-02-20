# PDF Text Replacement Pipeline

## Overview

This project provides a round-trip PDF transformation pipeline that converts born-digital PDFs to HTML, optionally modifies text content via JSON mappings, and renders the result back to PDF while preserving the original page dimensions.

**Workflow:** `PDF → HTML → [Text Replacement] → PDF`

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

### 4. PDF Page Size Extraction (`pdf_page_size.py`)

Uses PyMuPDF (`fitz`) to read the MediaBox dimensions of the first page.

**Returns:** `PageSize(width_pt, height_pt)` — dimensions in points (1 inch = 72 pt)

---

### 5. HTML to PDF Rendering (`render_html_to_pdf.py`)

Uses Playwright with headless Chromium to render HTML back to PDF.

**Configuration:**
- Zero margins (preserves absolute positioning from pdftohtml)
- Explicit width/height matching source PDF
- Prints background colors/images
- Uses `prefer_css_page_size=True` (⚠️ potential conflict with explicit dimensions)

---

### 6. HTML Normalization (`normalise_html_for_print.py`)

**Status:** Currently unused by CLI.

Provides CSS injection to force A4 page size and remove default margins. Would be useful for standardizing output but conflicts with the goal of preserving original PDF dimensions.

---

### 7. Placeholder Files

- `postprocess_pdf.py`: Empty — reserved for future PDF post-processing (e.g., metadata, compression)
- `replace_text_nodes.py`: Empty — possibly an incomplete refactoring remnant

---

## Data Flow

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

---

## Dependencies

| Tool/Library | Purpose | Installation |
|--------------|---------|--------------|
| `pdftohtml` | PDF → HTML conversion | Poppler utils (`apt install poppler-utils` or equivalent) |
| `PyMuPDF` (`fitz`) | PDF page size extraction | `pip install pymupdf` |
| `BeautifulSoup4` (`bs4`) | HTML parsing/modification | `pip install beautifulsoup4` |
| `lxml` | HTML parser backend | `pip install lxml` |
| `Playwright` | HTML → PDF rendering | `pip install playwright && playwright install chromium` |

---

## Usage

### Basic round-trip (no modifications):
```bash
python cli.py \
  --pdf-in document.pdf \
  --workdir ./work \
  --pdf-out output.pdf
```

### With text replacement:
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

---

## Known Limitations & Issues

### 1. Page Size Handling
The `render_html_to_pdf.py` module sets both:
- `prefer_css_page_size=True`
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
| Post-processing | Add `postprocess_pdf.py` for metadata preservation, PDF/A compliance |
| Font embedding | Ensure fonts are embedded or substituted correctly |
| Batch processing | Process multiple PDFs in parallel |
| OCR integration | Handle scanned/image-based PDFs |

---

## File Structure

```
doc_generator/
├── cli.py                      # Entry point & orchestration
├── convert_pdf_to_html.py      # PDF → HTML (Poppler)
├── replace_html_text.py        # HTML text modification (BeautifulSoup)
├── render_html_to_pdf.py       # HTML → PDF (Playwright)
├── pdf_page_size.py            # PDF dimension extraction (PyMuPDF)
├── normalise_html_for_print.py # CSS injection utilities (unused)
├── postprocess_pdf.py          # Placeholder for PDF post-processing
├── replace_text_nodes.py       # Placeholder/unfinished
├── ARCHITECTURE.md             # This document
└── ...                         # Sample PDFs, etc.
```
