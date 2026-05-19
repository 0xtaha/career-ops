"""generate_pdf — HTML → PDF via Playwright.

Port of generate-pdf.mjs. Applies ATS text normalization before rendering.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from career_ops_core.config import ProjectConfig


def _normalize_for_ats(html: str) -> tuple[str, dict[str, int]]:
    """Replace problematic Unicode chars in body text with ASCII equivalents.

    Skips content inside <style> and <script> tags.
    Returns (normalized_html, replacements_dict).
    """
    replacements: dict[str, int] = {}

    _REPLACEMENTS = [
        ("—", "-", "em-dash"),
        ("–", "-", "en-dash"),
        ("“", '"', "smart-double-quote"),
        ("”", '"', "smart-double-quote"),
        ("„", '"', "smart-double-quote"),
        ("‟", '"', "smart-double-quote"),
        ("‘", "'", "smart-single-quote"),
        ("’", "'", "smart-single-quote"),
        ("‚", "'", "smart-single-quote"),
        ("‛", "'", "smart-single-quote"),
        ("…", "...", "ellipsis"),
        ("​", "", "zero-width"),
        ("‌", "", "zero-width"),
        ("‍", "", "zero-width"),
        ("⁠", "", "zero-width"),
        ("﻿", "", "zero-width"),
        (" ", " ", "nbsp"),
    ]

    # Mask <style> and <script> blocks
    masks: list[str] = []
    masked = re.sub(
        r"<(style|script)\b[^>]*>[\s\S]*?</\1>",
        lambda m: f"\x00MASK{len(masks) - 1 + 1}\x00" if not masks.append(m.group(0)) else "",
        html,
        flags=re.IGNORECASE,
    )
    # Re-do with proper indexing
    masks = []

    def _mask(m: re.Match) -> str:
        idx = len(masks)
        masks.append(m.group(0))
        return f"\x00MASK{idx}\x00"

    masked = re.sub(r"<(style|script)\b[^>]*>[\s\S]*?</\1>", _mask, html, flags=re.IGNORECASE)

    def _sanitize(text: str) -> str:
        for src, dst, key in _REPLACEMENTS:
            count = text.count(src)
            if count:
                replacements[key] = replacements.get(key, 0) + count
                text = text.replace(src, dst)
        return text

    # Walk character by character between tags
    out_parts: list[str] = []
    i = 0
    while i < len(masked):
        lt = masked.find("<", i)
        if lt == -1:
            out_parts.append(_sanitize(masked[i:]))
            break
        out_parts.append(_sanitize(masked[i:lt]))
        gt = masked.find(">", lt)
        if gt == -1:
            out_parts.append(masked[lt:])
            break
        out_parts.append(masked[lt : gt + 1])
        i = gt + 1

    restored = "".join(out_parts)
    # Restore masked blocks
    for idx, block in enumerate(masks):
        restored = restored.replace(f"\x00MASK{idx}\x00", block)

    return restored, replacements


async def _do_generate(input_html: Path, output_pdf: Path, page_format: str) -> None:
    from playwright.async_api import async_playwright

    html_content = input_html.read_text(encoding="utf-8")
    normalized, replacements = _normalize_for_ats(html_content)
    if replacements:
        print("ATS normalization:", ", ".join(f"{k}={v}" for k, v in replacements.items()))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(normalized, wait_until="networkidle")
        await page.pdf(
            path=str(output_pdf),
            format=page_format.upper() if page_format.lower() in ("a4", "letter") else "A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()


def generate_pdf(
    cfg: ProjectConfig,
    input_html: Optional[Path] = None,
    output_pdf: Optional[Path] = None,
    page_format: str = "a4",
) -> None:
    import asyncio

    src = input_html or cfg.cv_template_html
    dst = output_pdf or (cfg.output_dir / "cv.pdf")
    if not src.exists():
        print(f"Error: input HTML not found: {src}")
        return
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating PDF: {src} → {dst}")
    asyncio.run(_do_generate(src, dst, page_format))
    print(f"✅ PDF saved: {dst}")
