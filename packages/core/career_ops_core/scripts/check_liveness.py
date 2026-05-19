"""check_liveness — Playwright-based job posting liveness checker.

Port of check-liveness.mjs. Returns True if all URLs are active, False if any expired.
"""
from __future__ import annotations

from career_ops_core.config import ProjectConfig
from career_ops_core.scripts.liveness_core import classify_liveness


async def run_liveness(cfg: ProjectConfig, urls: list[str]) -> bool:
    """Check each URL with Playwright; return True if all active."""
    from playwright.async_api import async_playwright

    if not urls:
        print("No URLs to check.")
        return True

    all_active = True

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()

        for url in urls:
            page = await context.new_page()
            try:
                resp = await page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                status = resp.status if resp else 0
                final_url = page.url
                body_text = await page.inner_text("body") if status < 400 else ""
                # Collect button/link text as apply control candidates
                apply_controls = await page.eval_on_selector_all(
                    "button, a[href], input[type=submit]",
                    "els => els.map(e => e.textContent || e.value || '')",
                )
                result = classify_liveness(
                    status=status,
                    final_url=final_url,
                    body_text=body_text,
                    apply_controls=apply_controls,
                )
            except Exception as e:
                result_label = "uncertain"
                reason = str(e)
                print(f"⚠️  {url}: {reason}")
                continue
            finally:
                await page.close()

            icon = {"active": "✅", "expired": "❌", "uncertain": "⚠️ "}.get(result.result, "?")
            print(f"{icon} {result.result.upper():10} {url}")
            print(f"   Reason: {result.reason}")
            if result.result == "expired":
                all_active = False

        await context.close()
        await browser.close()

    return all_active
