"""
diag_dump_open_chat.py
======================

Diagnostic: attach to the existing debug-Chrome on port 9222 and dump
whatever chat is currently open in the conversation panel.

Use:
  1. In debug-Chrome's WhatsApp Web window, manually click the
     "RITUAL TEACHERS / RITUAL TEACHERS" chat. Confirm the message
     panel on the right shows recent messages (Leah at 09:14, etc.).
  2. From PowerShell in the project root, run:
        python stage2\\diag_dump_open_chat.py
  3. Send back the printed output (counts + samples), and if asked,
     the saved channel_dump_open.html file.

The script makes no clicks, no scrolling, no search - it just snapshots
what's currently in the DOM and probes a range of selectors to see
which ones match the new WhatsApp Web layout.
"""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"
OUT_HTML = PROJECT_ROOT / "channel_dump_open.html"


def main() -> int:
    pw = sync_playwright().start()
    try:
        print(f"Attaching to {CDP_URL} ...")
        browser = pw.chromium.connect_over_cdp(CDP_URL)
        contexts = browser.contexts
        if not contexts:
            print("[FAIL] No browser contexts found.")
            return 1

        # Find the page whose URL is WhatsApp Web.
        page = None
        for ctx in contexts:
            for p in ctx.pages:
                url = (p.url or "").lower()
                if "web.whatsapp.com" in url:
                    page = p
                    break
            if page:
                break

        if page is None:
            print("[FAIL] No WhatsApp Web tab found.")
            return 1

        print(f"[OK] Attached to WhatsApp Web tab: {page.url}")

        # No navigation, no clicks. Just snapshot.
        html = page.content()
        OUT_HTML.write_text(html, encoding="utf-8")
        print(f"[OK] HTML saved to {OUT_HTML}  ({len(html):,} bytes)")

        # ---- Probe a wide range of selectors ----
        probes = [
            # Legacy
            "[data-pre-plain-text]",
            "div[data-pre-plain-text]",
            "[data-testid='msg-container']",
            "[role='article']",
            "[data-message-id]",
            ".message-in",
            ".message-out",
            # Likely new (ARIA-based)
            "[role='application']",
            "div#main",
            "div#main [role='row']",
            "div#main [role='gridcell']",
            "[data-id]",
            # Anything that smells like a message bubble
            "[class*='message']",
            "[class*='msg-']",
            # The most recent WA Web pattern: data-id starts with "true_" or "false_"
            "[data-id^='true_']",
            "[data-id^='false_']",
            "[data-id*='@']",
            # Copyable text
            ".copyable-text",
            "[copyable-text]",
            "span.selectable-text",
            "span[dir='auto']",
        ]
        print("\n[SELECTOR PROBES]")
        for sel in probes:
            try:
                count = len(page.query_selector_all(sel))
            except Exception as e:
                count = f"ERR: {e}"
            print(f"  {sel:50}  -> {count}")

        # If the new pattern is "data-id" based, print a few sample data-ids.
        print("\n[DATA-ID SAMPLES from div#main]")
        items = page.query_selector_all("div#main [data-id]")
        for i, it in enumerate(items[:8]):
            did = it.get_attribute("data-id") or ""
            text = (it.inner_text() or "").strip().replace("\n", " | ")
            print(f"  [{i}] data-id={did[:60]!r}  text={text[:120]!r}")

        # Try to surface the actual message text: look for copyable-text
        # containers and print up to 8 of them with neighbouring context.
        print("\n[COPYABLE-TEXT SAMPLES]")
        cts = page.query_selector_all("div.copyable-text, [data-pre-plain-text]")
        for i, ct in enumerate(cts[:8]):
            pre = ct.get_attribute("data-pre-plain-text") or ""
            inner = (ct.inner_text() or "").strip().replace("\n", " | ")
            print(f"  [{i}] pre={pre[:80]!r}")
            print(f"       text={inner[:160]!r}")

        return 0
    finally:
        try:
            pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
