# Architecture

## Overview

Doc Generator translates born-digital PDFs with two execution paths:

- `html` engine: `PDF -> HTML -> translate/replace -> PDF`
- `direct` engine: `PDF -> extract lines -> translate -> rewrite on original PDF`

Both paths are exposed via CLI and FastAPI.

## Runtime Entry Points

- CLI: [`cli.py`](./cli.py)
- API: [`app.main:app`](./app/main.py)

## High-Level Flows

### HTML Engine

1. Read first-page size from source PDF (`pdf_page_size.py`)
2. Convert PDF to HTML using Poppler `pdftohtml` (`convert_pdf_to_html.py`)
3. Apply either:
   - JSON mapping replacement (`replace_html_text.py`), or
   - LLM translation on HTML text nodes (`translator_llm.py`)
4. Render HTML back to PDF using Playwright Chromium (`render_html_to_pdf.py`)

### Direct Engine

1. Extract text lines with coordinates from source PDF (`translate_pdf_direct.py` using PyMuPDF)
2. Translate lines with LLM (OpenAI-compatible endpoint)
3. Remove source glyphs via text-only redaction in original line boxes
4. Write translated lines back via `insert_textbox` in the original PDF

## Module Layout

```text
app/
├── main.py                         # FastAPI app bootstrap
├── api/routes/
│   ├── health.py                   # GET /health
│   └── translate.py                # POST /translate/pdf
├── services/
│   └── pdf_translate_service.py    # Request validation + orchestration
└── pipeline/
    ├── convert_pdf_to_html.py
    ├── replace_html_text.py
    ├── pdf_page_size.py
    ├── render_html_to_pdf.py
    ├── translator_llm.py
    └── translate_pdf_direct.py
```

## CLI Behavior

Important flags:

- `--layout-engine {html,direct}`
- `--target-lang`
- `--source-lang` (optional)
- `--mapping-json` (html engine only)
- `--pdf-out`

Output naming:

- If `--pdf-out` is a directory, output is auto-generated:
  - translation: `<input_stem>_<target_lang>.pdf`
  - mapping: `<input_stem>_mapped.pdf`

## API Contract

### `POST /translate/pdf`

Multipart form fields:

- `file` (`.pdf`, required)
- `target_lang` (required for `layout_engine=direct`)
- `source_lang` (optional)
- `layout_engine` (`html` or `direct`, default `html`)
- `save_html` (boolean, html engine only)
- `mapping_json` (JSON string; mutually exclusive with `target_lang`)

Returns: translated PDF file response.

## Environment Variables

Used by current code:

- `RUNPOD_VLLM_HOST`
- `VLLM_API_KEY`
- `VLLM_MODEL`
- `DEFAULT_NUM_PREDICT`
- `COMBINE_NUM_PREDICT`
- `PER_REQUEST_TIMEOUT`

Reference sample: [`.env.sample`](./.env.sample)

## Dependencies

System:

- `poppler-utils` (`pdftohtml`, `pdftotext`, `pdfinfo`)
- Fonts with Unicode coverage (for non-Latin scripts in direct engine)

Python:

- `fastapi`, `uvicorn`, `python-multipart`
- `playwright`
- `pymupdf`
- `beautifulsoup4`, `lxml`
- `openai`, `python-dotenv`

## Deployment

- Local API: `uvicorn app.main:app --host 0.0.0.0 --port 9000`
- Docker: see [`Dockerfile`](./Dockerfile)
- Compose: see [`docker-compose.yml`](./docker-compose.yml)

