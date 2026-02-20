# cli.py

from __future__ import annotations

import argparse
from pathlib import Path

from convert_pdf_to_html import convert_pdf_to_html
from replace_html_text import load_mapping, replace_text_nodes
from render_html_to_pdf import render_html_to_pdf
from pdf_page_size import get_first_page_size


def main() -> int:
    """
    End-to-end:
      PDF -> HTML -> replace text -> PDF
    """
    ap = argparse.ArgumentParser(description="Round-trip PDF->HTML->PDF with text replacement.")
    ap.add_argument("--pdf-in", required=True, help="Input PDF path (born-digital).")
    ap.add_argument("--workdir", required=True, help="Working directory for intermediate files.")
    ap.add_argument("--mapping-json", required=False, default=None,
                    help="Optional JSON mapping of original text -> replacement text. If omitted, no text changes are applied.",
    )
    ap.add_argument("--pdf-out", required=True, help="Output PDF path.")
    args = ap.parse_args()

    pdf_in = Path(args.pdf_in).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve()
    pdf_out = Path(args.pdf_out).expanduser().resolve()

    if not pdf_in.exists():
        raise FileNotFoundError(f"Input PDF not found: {pdf_in}")

    page_size = get_first_page_size(pdf_in)

    html_dir = workdir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    # 1) Convert PDF -> HTML
    html_original = convert_pdf_to_html(pdf_in, html_dir)

    # 2) Replace text in HTML (optional)
    html_translated = html_dir / (pdf_in.stem + ".translated.html")

    if args.mapping_json:
        mapping_json = Path(args.mapping_json).expanduser().resolve()
        if not mapping_json.exists():
            raise FileNotFoundError(f"Mapping JSON not found: {mapping_json}")

        mapping = load_mapping(mapping_json)
        stats = replace_text_nodes(html_original, html_translated, mapping)
        html_for_pdf = html_translated
    else:
        stats = None
        html_for_pdf = html_original

    # 3) Render HTML -> PDF
    render_html_to_pdf(html_for_pdf, pdf_out, page_size=page_size)

    print(f"HTML original:   {html_original}")
    if stats is not None:
        print(f"HTML translated: {html_translated}")
        print(f"Replaced nodes:  {stats.replaced} (skipped: {stats.skipped})")
    else:
        print("No mapping provided: no text replacements applied.")
    print(f"PDF output:      {pdf_out}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
