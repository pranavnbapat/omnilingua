# Doc Generator

Translate born-digital PDFs while preserving layout as much as possible.

The project supports two engines:
- `html`: `PDF -> HTML -> translate -> PDF`
- `direct`: direct PDF line rewrite with coordinate-preserving replacement

## Features

- CLI workflow for PDF translation and JSON text replacement
- FastAPI endpoint for upload + translated PDF download
- Auto language detection (or manual `--source-lang`)
- Output auto-naming with language suffix when output is a directory
- Modular app structure (`app/api`, `app/services`, `app/pipeline`)

## Requirements

- Python 3.10+
- Poppler (`pdftohtml`, `pdftotext`, `pdfinfo`)
- Playwright Chromium (for `html` engine)
- LLM endpoint (OpenAI-compatible API)

Install system dependencies (Ubuntu/Debian example):

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

Install Python deps:

```bash
pip install -r requirements.txt
```

Install Playwright browser:

```bash
playwright install chromium
```

## Environment

Create `.env`:

```bash
LLM_API_URL=http://localhost:8000/v1
LLM_API_KEY=your-key
LLM_MODEL=qwen3-30b-a3b-awq

# Optional
LLM_MAX_TOKENS=8192
LLM_TEMPERATURE=0.1
LLM_BATCH_SIZE=50
PER_REQUEST_TIMEOUT=600
```

## CLI Usage

### 1) Direct engine (recommended for layout fidelity)

```bash
python cli.py \
  --pdf-in input/document.pdf \
  --workdir ./work \
  --target-lang es \
  --layout-engine direct \
  --pdf-out output/
```

If `--pdf-out` is a directory, output name is auto-generated as:
- `<input_stem>_<target_lang>.pdf` (example: `_es`)

### 2) HTML engine

```bash
python cli.py \
  --pdf-in input/document.pdf \
  --workdir ./work \
  --target-lang es \
  --layout-engine html \
  --pdf-out output/
```

### 3) JSON mapping replacement (HTML engine)

```bash
python cli.py \
  --pdf-in input/document.pdf \
  --workdir ./work \
  --mapping-json replacements.json \
  --layout-engine html \
  --pdf-out output/
```

`replacements.json` format:

```json
{
  "Hello": "Hola",
  "Summary": "Resumen"
}
```

## FastAPI Usage

Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health:

```bash
curl http://localhost:8000/health
```

Translate PDF (`direct`):

```bash
curl -X POST "http://localhost:8000/translate/pdf" \
  -F "file=@input/document.pdf" \
  -F "target_lang=es" \
  -F "layout_engine=direct" \
  -o output/document_es.pdf
```

Translate PDF (`html`):

```bash
curl -X POST "http://localhost:8000/translate/pdf" \
  -F "file=@input/document.pdf" \
  -F "target_lang=es" \
  -F "layout_engine=html" \
  -o output/document_es_html.pdf
```

## Project Structure

```text
doc_generator/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       └── translate.py
│   ├── services/
│   │   └── pdf_translate_service.py
│   └── pipeline/
│       ├── convert_pdf_to_html.py
│       ├── replace_html_text.py
│       ├── pdf_page_size.py
│       ├── render_html_to_pdf.py
│       ├── translator_llm.py
│       └── translate_pdf_direct.py
├── cli.py
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
```

## Notes

- `direct` engine is best for many layout-heavy documents, but some documents may still need tuning.
- For non-Latin scripts (Greek/Cyrillic/etc.), Unicode font fallback is used in direct mode.
- `work/` and `output/` are generated artifacts and should not be committed.

