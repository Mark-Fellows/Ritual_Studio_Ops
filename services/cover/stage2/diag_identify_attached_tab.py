"""
diag_identify_attached_tab.py
=============================

Tiny diagnostic that attaches to debug-Chrome on port 9222, picks the
WhatsApp Web page, brings it to the front, and changes its document.title
to a giant red marker. You then look at your Chrome windows on screen and
see which one has the marker - THAT is the window Playwright is acting on.

If the marker shows up on the Chrome window where you've been reading
Leah's message, we're on the same tab and the bug is elsewhere (e.g.
React render timing).

If the marker shows up on a DIFFERENT Chrome window (or a different
WhatsApp tab you didn't realise was open), we have window-identity
confusion and the production scraper has been talking to the wrong tab
all this time.
"""
from __future__ import annotations
import sys
import time
from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9222"


def main() -> int:
    pw = sync_playwright().start()
    try:
        print(f"Attaching to {CDP_URL} ...")
        browser = pw.chromium.connect_over_cdp(CDP_URL)

        # Enumerate every page in every context.
        n_contexts = len(browser.contexts)
        all_pages = []
        for ctx in browser.contexts:
            for p in ctx.pages:
                all_pages.append(p)

        print(f"[OK] Contexts: {n_contexts}; total pages: {len(all_pages)}")
        for i, p in enumerate(all_pages):
            try:
                t = p.title()
            except Exception:
                t = "(title unavailable)"
            print(f"  [{i}] url={p.url}")
            print(f"       title={t!r}")

        # Pick the WhatsApp Web page.
        wa_pages = [p for p in all_pages if "web.whatsapp.com" in (p.url or "").lower()]
        if not wa_pages:
            print("[FAIL] No WhatsApp Web tab found.")
            return 1
        if len(wa_pages) > 1:
            print(f"[NOTE] {len(wa_pages)} WhatsApp Web pages found. Marking ALL of them.")

        for i, page in enumerate(wa_pages):
            print(f"\n[{i}] Marking tab: {page.url}")
            try:
                page.bring_to_front()
            except Exception as e:
                print(f"     bring_to_front failed: {e}")

            # Change the document.title so the browser's tab caption changes.
            # We pulse it a few times so it's unmistakable in the OS tab bar.
            try:
                page.evaluate("""
                    () => {
                      const orig = document.title;
                      window.__playwrightMarker = window.__playwrightMarker || setInterval(() => {
                        document.title = (document.title.startsWith('>>>'))
                          ? orig
                          : '>>> PLAYWRIGHT IS HERE <<<';
                      }, 700);
                      setTimeout(() => {
                        clearInterval(window.__playwrightMarker);
                        window.__playwrightMarker = null;
                        document.title = orig;
                      }, 20000);
                    }
                """)
                print("     [OK] Title-pulse marker injected for ~20 seconds.")
            except Exception as e:
                print(f"     evaluate failed: {e}")

        print("\nLook at your Chrome windows now.")
        print("Whichever Chrome WINDOW has its TITLE BAR / TAB CAPTION flashing")
        print("between the chat name and '>>> PLAYWRIGHT IS HERE <<<' is the")
        print("one Playwright is acting on.")
        print("\nLeaving the marker active for 20 seconds; sleeping...")
        time.sleep(20)
        return 0
    finally:
        try:
            pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
