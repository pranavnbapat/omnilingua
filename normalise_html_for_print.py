# normalise_html_for_print.py

from __future__ import annotations

from pathlib import Path


PRINT_CSS = """
<style>
  @page { size: A4; margin: 0; }
  html, body { margin: 0; padding: 0; background: white; }
</style>
"""


def inject_print_css(html_path: Path) -> None:
    """
    Inject print CSS to stabilise Chromium PDF output:
    - force A4
    - remove default margins
    - ensure white background (avoid grey filler pages)
    """
    s = html_path.read_text(encoding="utf-8", errors="ignore")
    if "</head>" in s:
        s = s.replace("</head>", PRINT_CSS + "\n</head>", 1)
    else:
        # Fallback: prepend if <head> is missing (rare)
        s = PRINT_CSS + "\n" + s
    html_path.write_text(s, encoding="utf-8")
