# render_html_to_pdf.py

from __future__ import annotations

import asyncio

from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from pdf_page_size import PageSize


def pt_to_in(pt: float) -> float:
    # 1 inch = 72 points
    return pt / 72.0


async def _render_with_chromium(html_path: Path, pdf_path: Path, page_size: PageSize) -> None:
    """
    Render HTML to PDF using headless Chromium, matching the source PDF page size.
    """
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    margins: Any = {"top": "0", "right": "0", "bottom": "0", "left": "0"}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto(html_path.as_uri(), wait_until="networkidle")

        await page.pdf(
            path=str(pdf_path),
            print_background=True,
            prefer_css_page_size=True,
            width=f"{pt_to_in(page_size.width_pt):.4f}in",
            height=f"{pt_to_in(page_size.height_pt):.4f}in",
            margin=margins,
        )

        await browser.close()


def render_html_to_pdf(html_path: Path, pdf_path: Path, page_size: PageSize) -> None:
    """
    Synchronous wrapper.
    """
    asyncio.run(_render_with_chromium(html_path, pdf_path, page_size))
