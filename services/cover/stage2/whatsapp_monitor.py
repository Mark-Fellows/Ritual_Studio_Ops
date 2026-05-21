"""
whatsapp_monitor.py — Stage 2
==============================
Reads recent messages from configured WhatsApp community channels via
WhatsApp Web in Chrome (Playwright).

Two connection modes
--------------------
1. ATTACH  — connects to an already-running Chrome instance that was
   started with --remote-debugging-port=9222.  WhatsApp Web must
   already be logged in.  This is the preferred mode for production
   because it reuses your existing session and avoids QR re-scans.

2. LAUNCH  — Playwright launches a fresh Chromium instance with a
   persistent profile directory so the WhatsApp Web session is saved
   between runs.  Useful for first-time setup or if Chrome is closed.

Usage
-----
    python whatsapp_monitor.py              # attach mode (default)
    python whatsapp_monitor.py --launch     # launch mode
    python whatsapp_monitor.py --hours 12   # override lookback window

Prerequisites
-------------
    pip install playwright
    playwright install chromium

    For ATTACH mode, start Chrome first:
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            --remote-debugging-port=9222
            --user-data-dir="C:\\ChromeDebug"
"""

import sys
import time
import argparse
import json
import re
from typing import Any
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -- Adjust path so we can import config.py from the parent directory --
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CHROME_DEBUG_PORT,
    CHROME_PATH,
    WHATSAPP_LOOKBACK_HOURS,
    sb_post,
    sb_patch,
)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

WHATSAPP_WEB_URL = "https://web.whatsapp.com"

# Playwright wait timeouts (ms)
PAGE_LOAD_TIMEOUT = 120_000
ELEMENT_TIMEOUT = 15_000
SHORT_WAIT = 3_000

# Persistent profile dir for LAUNCH mode (saves WhatsApp Web session)
PROFILE_DIR = str(Path.home() / "AppData" / "Local" / "CoverMgmt" / "chrome_profile")

# WhatsApp Web selectors
# NOTE: WhatsApp Web's DOM changes periodically. If selectors stop working,
# inspect the page and update these constants — the aria-label attributes
# are generally more stable than class names.
SEL_SEARCH_BOX = "input[placeholder]"
SEL_CHAT_LIST_ITEM = '[role="row"]'
SEL_CHAT_LIST = '[aria-label="Chat list"]'
SEL_PANE_TITLE = "#pane-side span[title]"
SEL_MSG_IN = "div.message-in, div.message-out"
SEL_MSG_BUBBLE = "[data-pre-plain-text]"
SEL_MSG_TEXT = "span[data-testid='selectable-text']"
SEL_COMMUNITY_ICON = 'span[data-icon="newsletter"]'
SEL_CHANNELS_HEADER = 'span[title="Channels"], div[aria-label="Channels"]'

# Regex: parse WhatsApp message timestamp attribute
# Format: "[HH:MM, DD/MM/YYYY] Name: "
_TS_RE = re.compile(r"\[(\d{1,2}:\d{2}),\s*(\d{1,2}/\d{1,2}/\d{4})\]\s*(.+?):\s*$")

# Brisbane / AEST is permanently UTC+10 (Queensland does not observe DST).
# Attaching this timezone ensures timestamps are stored correctly in Supabase
# (which treats naive datetimes as UTC, causing a 10-hour display error).
_BRISBANE_TZ = timezone(timedelta(hours=10))


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────


class ChannelMessage:
    __slots__ = (
        "community",
        "channel",
        "sender",
        "timestamp",
        "text",
        "_channel_db_id",
        "original_sender",  # For quoted/replied messages
        "is_reply",  # Whether this is a reply to another message
    )

    def __init__(
        self,
        community: str,
        channel: str,
        sender: str,
        timestamp: datetime | None,
        text: str,
        original_sender: str | None = None,
        is_reply: bool = False,
    ):
        self.community = community
        self.channel = channel
        self.sender = sender  # The person who sent this message (replier if quoted)
        self.timestamp = timestamp
        self.text = text
        self._channel_db_id = None
        self.original_sender = original_sender  # Original requester if this is a reply
        self.is_reply = is_reply  # True if this message is replying to another

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else "?"
        if self.is_reply and self.original_sender:
            return (
                f"<Msg channel={self.channel!r} sender={self.sender!r} "
                f"original_sender={self.original_sender!r} "
                f"ts={ts} text={self.text[:60]!r}>"
            )
        return (
            f"<Msg channel={self.channel!r} sender={self.sender!r} "
            f"ts={ts} text={self.text[:60]!r}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Timestamp parsing
# ─────────────────────────────────────────────────────────────────────────────


def parse_wa_timestamp(pre_plain_text: str) -> tuple[str, datetime | None]:
    """
    Parse the data-pre-plain-text attribute.
    Returns (sender_name, datetime_or_None).
    """
    m = _TS_RE.match(pre_plain_text.strip())
    if not m:
        return ("Unknown", None)

    time_str, date_str, sender = m.group(1), m.group(2), m.group(3).strip()
    try:
        ts = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M").replace(tzinfo=_BRISBANE_TZ)
    except ValueError:
        ts = None
    return sender, ts


def extract_quoted_sender_from_dom(bubble) -> str | None:
    """
    Detect a WhatsApp quote-reply by inspecting the DOM element, not the text.

    When a user selects a message and taps Reply, WhatsApp Web renders a
    quoted block using ``data-testid="quoted-message"`` (current stable selector)
    with ``._ahxj`` as a class-name fallback for resilience.  The quoted sender
    name is identified via ``data-testid="author"`` (with ``._ahxt`` fallback).

    Two structural variants exist:

    Variant A — text-to-text replies:
        parent
          [data-testid="quoted-message"]   ← quoted block (sibling of the bubble)
            [data-testid="author"] span    ← quoted sender name
          copyable-text[data-pre-plain-text]   ← our matched bubble
            selectable-text span               ← reply text

    Variant B — outer copyable-text (image/media replies):
        copyable-text[data-pre-plain-text]   ← our matched bubble
          [data-testid="quoted-message"]     ← quoted block inside bubble
            [data-testid="author"] span      ← quoted sender name
          (reply content)

    NOTE: WhatsApp Web obfuscated class names (_ahxj, _ahxt) changed in May 2026.
    The data-testid attributes are stable across deploys.

    Returns the quoted sender name, or None if this is not a quote-reply.
    """
    try:
        return bubble.evaluate("""el => {
            // Locate the quoted-message block using stable data-testid (current WA Web)
            // with private-class fallbacks for resilience against future renames.
            function findQuotedBlock(root) {
                return root.querySelector('[data-testid="quoted-message"]')
                    || root.querySelector('._ahxj')
                    || null;
            }
            function senderFromBlock(block) {
                if (!block) return null;
                const a = block.querySelector('[data-testid="author"]')
                       || block.querySelector('._ahxt');
                return a ? a.textContent.trim() || null : null;
            }

            // Variant A: quoted block lives in the parent element (text-to-text reply)
            const parent = el.parentElement;
            if (parent) {
                const qb = findQuotedBlock(parent);
                if (qb && !el.contains(qb)) {
                    const name = senderFromBlock(qb);
                    if (name) return name;
                }
            }
            // Variant B: quoted block is a descendant of the bubble (media/outer reply)
            const inner = findQuotedBlock(el);
            if (inner) {
                const name = senderFromBlock(inner);
                if (name) return name;
            }
            return null;
        }""")
    except Exception:
        return None


def extract_quoted_message_info(text: str) -> tuple[str | None, str]:
    """
    Legacy text-based heuristic for quoted-reply detection.
    Kept for reference only — superseded by extract_quoted_sender_from_dom()
    which uses the reliable DOM structure rather than text pattern matching.
    Returns (None, text) unconditionally so it has no effect on live runs.
    """
    return None, text


def is_within_window(ts: datetime | None, hours: int) -> bool:
    """Return True if ts is within the last `hours` hours."""
    if ts is None:
        return True  # include if we cannot parse the timestamp
    cutoff = datetime.now(tz=_BRISBANE_TZ) - timedelta(hours=hours)
    return ts >= cutoff


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp Web navigation helpers
# ─────────────────────────────────────────────────────────────────────────────


def wait_for_wa_loaded(page) -> None:
    """Wait until WhatsApp Web's main interface is visible."""
    print("  Waiting for WhatsApp Web to load...")
    try:
        page.wait_for_selector("#pane-side", timeout=PAGE_LOAD_TIMEOUT)
        print("  [OK] WhatsApp Web loaded.")
    except Exception as e:
        # If it's a timeout, guide the user
        if "Timeout" in str(e):
            print("  [FAIL] Timeout waiting for WhatsApp Web to load.")
            print("  Make sure to:")
            print("    1. Scan the QR code if this is the first run")
            print("    2. Wait for WhatsApp to fully load (may take 30-60 seconds)")
            print("    3. Check that the browser tab shows the conversation list")
            raise
        raise


def navigate_to_channel(page, community_name: str, channel_name: str) -> bool:
    """
    Navigate to a specific community channel in WhatsApp Web.
    Returns True if successful, False if not found.

    Strategy:
    1. Use the search box to find the channel by name.
    2. If not found via search, scroll the chat list looking for it.
    """
    print(f"  Navigating to [{community_name}] -> [{channel_name}]...")

    # Dismiss any open panels / overlays (e.g. info panes, tooltips) that may
    # intercept pointer events on the chat list.  Safe to call even if nothing
    # is open — Escape is a no-op on the main chat list view.
    try:
        page.keyboard.press("Escape")
        time.sleep(0.3)
    except Exception:
        pass

    # ── Strategy 1: Search box ────────────────────────────────────────────────
    try:
        search = page.wait_for_selector(SEL_SEARCH_BOX, timeout=ELEMENT_TIMEOUT)
        search.click()
        search.fill("")
        page.keyboard.type(channel_name, delay=50)
        time.sleep(1.5)

        # Look for a chat-list row whose text contains the channel_name
        items = page.query_selector_all(SEL_CHAT_LIST_ITEM)
        for item in items:
            try:
                text = item.inner_text() or ""
                if channel_name.strip().lower() in text.strip().lower():
                    # IMPORTANT (2026-05-17 fix):
                    # Use Playwright's native click FIRST. As of mid-2026,
                    # WhatsApp Web requires the full pointer-event sequence
                    # (pointerdown -> pointerup -> click) to open a chat -
                    # a bare DOM `el.click()` no longer triggers the React
                    # handler that mounts the conversation panel. Symptom
                    # before this fix: search returned the right row and
                    # JS click reported success, but the chat never opened
                    # so the conversation-panel DOM was never mounted and
                    # the scraper saw zero messages.
                    #
                    # We pass force=True to skip Playwright's actionability
                    # check (originally the reason for the JS-click hack -
                    # floating panels intercepting pointer events).
                    try:
                        item.click(force=True)
                    except Exception as pw_e:
                        err_str = str(pw_e)
                        if "not attached" in err_str.lower():
                            # WhatsApp Web's virtual list re-rendered the element
                            # between query_selector_all and the click attempt.
                            # Re-query immediately with page.locator() which
                            # re-resolves the element on every action and
                            # cannot go stale. JS el.click() is NOT used as a
                            # fallback here because it bypasses the pointer-event
                            # sequence WhatsApp Web's React handler requires (see
                            # 2026-05-17 fix comment above).
                            print("  [WARN] Element detached — re-querying with locator...")
                            try:
                                page.locator(
                                    SEL_CHAT_LIST_ITEM, has_text=channel_name
                                ).first.click(force=True, timeout=4000)
                            except Exception as retry_e:
                                print(f"  [WARN] Re-query click also failed ({retry_e}); skipping row")
                                continue
                        else:
                            print(f"  [WARN] Playwright click failed ({pw_e}); falling back to JS click")
                            try:
                                item.evaluate("el => el.click()")
                            except Exception as js_e:
                                print(f"  [WARN] JS click also failed: {js_e}")
                                continue
                    # Clear the search box BEFORE waiting so its focus
                    # change doesn't suppress the chat-open transition.
                    try:
                        search.fill("")
                        search.press("Escape")
                    except Exception:
                        pass
                    # Wait for the conversation panel to actually mount
                    # before declaring success. msg-container is the
                    # cheapest indicator that messages are now rendered;
                    # we fall back to data-pre-plain-text in case Meta
                    # toggles one but not the other on a future update.
                    panel_ready = False
                    for sel in ("[data-testid='msg-container']", "[data-pre-plain-text]"):
                        try:
                            page.wait_for_selector(sel, timeout=6000)
                            panel_ready = True
                            break
                        except Exception:
                            continue
                    if not panel_ready:
                        print(f"  [WARN] Clicked {channel_name} but conversation panel did not mount within 6s")
                        # Continue anyway - the caller will see zero messages
                        # and we'll have a clue in the logs.
                    else:
                        print(f"  [+] Found via search: {channel_name}")
                    return True
            except Exception as inner_e:
                # Skip rows we can't read; keep searching.
                continue

        # Clear search if not found
        search.fill("")
        search.press("Escape")
    except Exception as e:
        print(f"  Search strategy failed: {e}")

    print(f"  [!] Channel not found: {channel_name}")
    return False


def read_messages_from_current_channel(
    page, community: str, channel: str, lookback_hours: int
) -> list[ChannelMessage]:
    """
    Reads messages from the currently open channel.
    Scrolls up to retrieve older messages within the lookback window.
    Returns a list of ChannelMessage objects.
    """
    messages: list[ChannelMessage] = []
    prev_count = 0
    scroll_attempts = 0
    max_scrolls = 20  # safety limit

    while scroll_attempts < max_scrolls:
        # Collect all message bubbles currently in DOM
        bubbles = page.query_selector_all(SEL_MSG_BUBBLE)

        for bubble in bubbles:
            pre_text = bubble.get_attribute("data-pre-plain-text") or ""
            sender, ts = parse_wa_timestamp(pre_text)

            if not is_within_window(ts, lookback_hours):
                continue  # older than window — skip

            # Extract message text, excluding the quoted block in reply bubbles.
            #
            # WhatsApp Web Variant B reply bubbles have this DOM structure:
            #   copyable-text[data-pre-plain-text]        ← our matched bubble
            #     ._ahxj._ahxz                            ← quoted block
            #       span[data-testid='selectable-text']   ← QUOTED text (skip this)
            #     span[data-testid='selectable-text']     ← REPLY text  (want this)
            #
            # The original single-selector query_selector(SEL_MSG_TEXT) returns
            # the first matching span, which for Variant B is inside the quoted
            # block — giving us the quoted text instead of the reply text.
            #
            # Fix (2026-05-19): use JS to walk all selectable-text spans and
            # return the first one that is NOT a descendant of ._ahxj (the
            # quoted block). Falls back to the first span if none found outside
            # the quoted block, preserving the previous behaviour for messages
            # that have no quoted block at all.
            try:
                text = bubble.evaluate("""el => {
                    // Use stable data-testid; fall back to private class if renamed again.
                    const quotedBlock = el.querySelector('[data-testid="quoted-message"]')
                                     || el.querySelector('._ahxj')
                                     || null;
                    const spans = el.querySelectorAll("span[data-testid='selectable-text']");
                    for (const span of spans) {
                        if (!quotedBlock || !quotedBlock.contains(span)) {
                            return span.innerText.trim();
                        }
                    }
                    // Fallback: first span regardless (no quoted block present)
                    const first = el.querySelector("span[data-testid='selectable-text']");
                    return first ? first.innerText.trim() : '';
                }""") or ""
            except Exception:
                text_el = bubble.query_selector(SEL_MSG_TEXT)
                text = text_el.inner_text().strip() if text_el else ""
            if not text:
                continue

            # Detect WhatsApp quote-reply via DOM (reliable) rather than text heuristics.
            # quoted_sender = the person being replied to (e.g. Ines);
            # sender        = the person who sent this message (e.g. Kate Rafferty).
            quoted_sender = extract_quoted_sender_from_dom(bubble)
            is_reply = quoted_sender is not None

            if is_reply:
                print(f"    [reply] {sender!r} quoted {quoted_sender!r} (text: {text[:60]!r})")

            msg = ChannelMessage(
                community,
                channel,
                sender,           # always the actual author of this message
                ts,
                text,
                original_sender=quoted_sender,  # person being replied to, or None
                is_reply=is_reply,
            )

            # Deduplicate by (sender, timestamp, first 40 chars of text)
            key = (sender, ts, text[:40])
            if not any((m.sender, m.timestamp, m.text[:40]) == key for m in messages):
                messages.append(msg)

        # If no new messages appeared after scroll, we've reached the top
        if len(messages) == prev_count and scroll_attempts > 0:
            break

        prev_count = len(messages)

        # Check if the oldest visible message is already outside our window
        if bubbles:
            first_pre = bubbles[0].get_attribute("data-pre-plain-text") or ""
            _, oldest_ts = parse_wa_timestamp(first_pre)
            if oldest_ts and not is_within_window(oldest_ts, lookback_hours):
                break  # scrolled far enough back

        # Scroll up to load older messages
        chat_area = page.query_selector("div#main")
        if chat_area:
            page.evaluate("(el) => { el.scrollTop = 0; }", chat_area)
        else:
            page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1.5)
        scroll_attempts += 1

    print(f"  -> {len(messages)} messages in window from [{channel}]")
    return messages


# ─────────────────────────────────────────────────────────────────────────────
# Run log helpers
# ─────────────────────────────────────────────────────────────────────────────


def create_run_log(channels: list[str]) -> str:
    """Insert a monitor run row and return its run_id."""
    row = sb_post(
        "whatsapp_monitor_runs",
        {
            "channels_checked": channels,
            "run_status": "running",
        },
    )
    run_id = row[0]["monitor_run_id"]
    print(f"Run ID: {run_id}")
    return run_id


def complete_run_log(
    run_id: str,
    messages_read: int,
    requests_found: int,
    status: str = "completed",
    error: str | None = None,
) -> None:
    sb_patch(
        "whatsapp_monitor_runs",
        {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "messages_read": messages_read,
            "requests_found": requests_found,
            "run_status": status,
            "error_message": error,
        },
        match_params={"monitor_run_id": f"eq.{run_id}"},
    )


def update_run_requests_found(run_id: str, count: int) -> None:
    """Update requests_found on an existing run row.

    Called by cover_processor after NLP has classified the messages.
    complete_run_log() initialises requests_found=0 because the monitor
    itself does not classify; the classifier (cover_processor) calls
    this function to set the real value.
    """
    if not run_id:
        return
    sb_patch(
        "whatsapp_monitor_runs",
        {"requests_found": count},
        match_params={"monitor_run_id": f"eq.{run_id}"},
    )



# ─────────────────────────────────────────────────────────────────────────────
# Main monitor class
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppMonitor:
    """
    Reads WhatsApp community channel messages via Playwright.
    Call .run() to execute a monitoring session.
    """

    def __init__(
        self, lookback_hours: int = WHATSAPP_LOOKBACK_HOURS, launch_mode: bool = False
    ):
        self.lookback_hours = lookback_hours
        self.launch_mode = launch_mode
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None
        self.last_run_id: str | None = None

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    def _start_browser(self) -> None:
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        pw = self._playwright

        if self.launch_mode:
            print(f"Launching Chromium (profile: {PROFILE_DIR})…")
            self._browser = pw.chromium.launch_persistent_context(
                user_data_dir=PROFILE_DIR,
                headless=False,
                args=["--no-sandbox"],
                executable_path=CHROME_PATH if Path(CHROME_PATH).exists() else None,
            )
            self._page = (
                self._browser.pages[0]
                if self._browser.pages
                else self._browser.new_page()
            )
            # Navigate to WhatsApp Web
            print("  Opening WhatsApp Web...")
            self._page.goto(WHATSAPP_WEB_URL, timeout=PAGE_LOAD_TIMEOUT)
            # Wait for user to scan QR code if first login
            print("  If this is the first run, scan the QR code in the browser window.")
            print("  Waiting for WhatsApp Web to fully load...")
        else:
            print(f"Attaching to Chrome on port {CHROME_DEBUG_PORT}...")
            try:
                self._browser = pw.chromium.connect_over_cdp(
                    f"http://localhost:{CHROME_DEBUG_PORT}"
                )
            except Exception as e:
                sys.exit(
                    f"Cannot connect to Chrome on port {CHROME_DEBUG_PORT}.\n"
                    f"Start Chrome with:\n"
                    f"  chrome.exe --remote-debugging-port={CHROME_DEBUG_PORT} "
                    f'--user-data-dir="C:\\\\ChromeDebug"\n\nError: {e}'
                )
            # Use the first context / page that has WhatsApp Web, or create one
            ctx = self._browser.contexts[0]
            wa_pages = [p for p in ctx.pages if "web.whatsapp.com" in p.url]
            if wa_pages:
                self._page = wa_pages[0]
                print("  Found existing WhatsApp Web tab.")
            else:
                self._page = ctx.new_page()
                print("  Opening WhatsApp Web...")
                self._page.goto(WHATSAPP_WEB_URL, timeout=PAGE_LOAD_TIMEOUT)

    def _stop_browser(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    # ── Channel loading ───────────────────────────────────────────────────────

    def _load_active_channels(self) -> list[dict]:
        """Fetch active channels from Supabase, ordered by monitor_order."""
        from config import sb_get

        rows = sb_get(
            "whatsapp_channels",
            params={
                "is_active": "eq.true",
                "order": "monitor_order",
                "select": "whatsapp_channel_id,community_name,channel_name",
            },
        )
        return rows

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> list[ChannelMessage]:
        """
        Execute a monitoring session.
        Returns all messages collected across all channels.
        """
        print(f'\n{"="*60}')
        print(f"WhatsApp Monitor - lookback {self.lookback_hours}h")
        print(f'{"="*60}\n')

        channels = self._load_active_channels()
        if not channels:
            print("No active channels configured in whatsapp_channels table.")
            return []

        channel_labels = [
            f'{c["community_name"]} / {c["channel_name"]}' for c in channels
        ]
        print(f"Channels to check ({len(channels)}):")
        for label in channel_labels:
            print(f"  - {label}")
        print()

        # Create run log entry
        run_id = create_run_log(channel_labels)
        self.last_run_id = run_id

        all_messages: list[ChannelMessage] = []

        try:
            self._start_browser()
            wait_for_wa_loaded(self._page)

            for ch in channels:
                community = ch["community_name"]
                channel = ch["channel_name"]
                ch_id = ch["whatsapp_channel_id"]

                print(f"\n-- {community} / {channel} --")
                ok = navigate_to_channel(self._page, community, channel)
                if not ok:
                    print(f"  Skipping (channel not found in WhatsApp Web).")
                    continue

                # Allow chat to load
                time.sleep(SHORT_WAIT / 1000)

                msgs = read_messages_from_current_channel(
                    self._page, community, channel, self.lookback_hours
                )
                # Attach the Supabase channel ID for later use
                for m in msgs:
                    m._channel_db_id = ch_id
                all_messages.extend(msgs)

            complete_run_log(
                run_id,
                messages_read=len(all_messages),
                requests_found=0,  # updated by cover_processor after NLP
                status="completed",
            )

        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            complete_run_log(run_id, len(all_messages), 0, "partial")
        except Exception as e:
            print(f"\nError during monitoring: {e}")
            complete_run_log(run_id, len(all_messages), 0, "failed", str(e))
            raise
        finally:
            if not self.launch_mode:
                # Don't close in attach mode — leave Chrome open
                self._playwright.stop() if self._playwright else None
            else:
                self._stop_browser()

        print(f"\nTotal messages collected: {len(all_messages)}")
        return all_messages


# =========================================================================
# Debug inspection helper
# =========================================================================


def debug_inspect_page(page, filepath: str = "page_structure.txt") -> None:
    """
    Inspect the WhatsApp Web page and save the structure to a file.
    Helps identify correct selectors when WhatsApp Web UI changes.
    """
    print(f"\nDEBUG: Inspecting page structure...")
    print(f"DEBUG: Current URL: {page.url}")

    # Test various selector strategies
    selectors_to_test = [
        ("=== SEARCH / INPUT ===", ""),
        ("Search box (old selector)", SEL_SEARCH_BOX),
        ("Search box (contenteditable)", 'div[contenteditable="true"]'),
        ("Search box (input with placeholder)", "input[placeholder]"),
        ("=== CHAT/CHANNEL LIST ===", ""),
        ("Chat list items (listitem role)", SEL_CHAT_LIST_ITEM),
        ("Chat list items (data-testid)", "div[data-testid='conversation-list-item']"),
        ("Chat list items (aria-label)", "div[aria-label*='RITUAL']"),
        ("All divs in pane-side", "#pane-side > div > div"),
        ("List item any", "[role='option']"),
        ("List item link", "a[href*='c/']"),
        ("List rows", "div[data-testid='list'] > div"),
        ("=== NAVIGATION ===", ""),
        ("Pane side", "#pane-side"),
        ("Sidebar container", "div[data-testid='sidebar']"),
        ("Main container", "div[data-testid='app']"),
        ("=== COMMUNITY/CHANNEL INDICATORS ===", ""),
        ("Communities header", 'span[title="Communities"]'),
        ("Channels header", SEL_CHANNELS_HEADER),
        ("Community icon", SEL_COMMUNITY_ICON),
        ("Newsletter icon", 'span[data-icon="newsletter"]'),
    ]

    print("\n" + "=" * 70)
    print("SELECTOR TEST RESULTS:")
    print("=" * 70)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Page Structure Inspection\n")
        f.write(f"URL: {page.url}\n")
        f.write(f"=" * 70 + "\n\n")

        for label, selector in selectors_to_test:
            # Skip section headers (empty selectors)
            if not selector:
                print(f"\n{label}")
                f.write(f"\n{label}\n")
                continue

            try:
                elements = page.query_selector_all(selector)
                count = len(elements)
                status = "FOUND" if count > 0 else "NOT FOUND"
                msg = f"[{status:9}] {label:40} | Selector: {selector} | Count: {count}"
                print(msg)
                f.write(msg + "\n")

                # If found, print some details
                if count > 0 and count <= 3:
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = (
                                elem.inner_text()[:50]
                                if elem.inner_text()
                                else "(empty)"
                            )
                            detail = f"           -> [{i}] Text: {text}"
                            print(detail)
                            f.write(detail + "\n")
                        except:
                            pass
            except Exception as e:
                msg = f"[ERROR    ] {label:40} | Error: {str(e)[:60]}"
                print(msg)
                f.write(msg + "\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("USEFUL HTML SNIPPETS:\n")
        f.write("=" * 70 + "\n")

        # Try to get the pane-side HTML to see chat item structure
        try:
            pane = page.query_selector("#pane-side")
            if pane:
                f.write("\n[PANE-SIDE INNER HTML (first 3000 chars)]:\n")
                f.write("-" * 70 + "\n")
                inner_html = page.evaluate("el => el.innerHTML", pane)
                f.write(inner_html[:3000])
        except:
            pass

        f.write("\n\n" + "=" * 70 + "\n")
        f.write("Full Page HTML (first 5000 chars):\n")
        f.write("=" * 70 + "\n")
        html = page.content()
        f.write(html[:5000])

    print(f"\nDEBUG: Results saved to {filepath}")
    print("\nIMPORTANT: Please review the selectors above.")
    print("The ones marked [FOUND] are working. Use those to update SEL_* constants.")


# =========================================================================
# CLI entry point
# =========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read WhatsApp community channel messages"
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch a new Chrome instance (default: attach to existing)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: inspect page structure and selectors, then exit",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=WHATSAPP_LOOKBACK_HOURS,
        help=f"Hours of messages to retrieve (default: {WHATSAPP_LOOKBACK_HOURS})",
    )
    parser.add_argument(
        "--dump-channel",
        type=str,
        help="Navigate to a channel and dump its HTML structure (e.g., 'RITUAL DIARY')",
    )
    args = parser.parse_args()

    # Debug mode: just inspect and exit
    if args.debug:
        print("\nStarting WhatsApp Monitor in DEBUG mode...")
        # Default to attach mode (port 9222) so the diagnostic uses the
        # already-logged-in debug-Chrome session. Pass --launch only when
        # you really want to start a fresh Chrome from scratch.
        monitor = WhatsAppMonitor(
            lookback_hours=args.hours, launch_mode=args.launch
        )
        try:
            monitor._start_browser()
            wait_for_wa_loaded(monitor._page)
            debug_inspect_page(monitor._page)
        finally:
            monitor._stop_browser()
        return

    # Dump channel mode: navigate to a channel and save its HTML
    if args.dump_channel:
        print(f"\nDumping channel: {args.dump_channel}...")
        # Default to attach mode (port 9222) so the diagnostic uses the
        # already-logged-in debug-Chrome session. Pass --launch only when
        # you really want to start a fresh Chrome from scratch.
        monitor = WhatsAppMonitor(
            lookback_hours=args.hours, launch_mode=args.launch
        )
        try:
            monitor._start_browser()
            wait_for_wa_loaded(monitor._page)
            # Navigate to the channel
            ok = navigate_to_channel(
                monitor._page, "RITUAL TEACHERS", args.dump_channel
            )
            if ok:
                time.sleep(2)  # Let messages load
                # Save the HTML
                html = monitor._page.content()
                with open("channel_dump.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"[OK] Channel HTML saved to channel_dump.html")

                # Also test message selectors
                bubbles = monitor._page.query_selector_all(SEL_MSG_BUBBLE)
                print(
                    f"[OK] Found {len(bubbles)} message bubbles with selector: {SEL_MSG_BUBBLE}"
                )

                # Parse and analyze each message
                print(f"\n[TIMESTAMP ANALYSIS]")
                print(f"Current time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                print(f"Lookback window: {args.hours} hours")
                cutoff = datetime.now() - timedelta(hours=args.hours)
                print(f"Cutoff time: {cutoff.strftime('%d/%m/%Y %H:%M:%S')}\n")

                for i, bubble in enumerate(bubbles[:10]):  # First 10 messages
                    pre_text = bubble.get_attribute("data-pre-plain-text") or ""
                    sender, ts = parse_wa_timestamp(pre_text)
                    within_window = is_within_window(ts, args.hours)

                    text_el = bubble.query_selector(SEL_MSG_TEXT)
                    text = text_el.inner_text().strip() if text_el else "(no text)"

                    ts_str = ts.strftime("%d/%m/%Y %H:%M") if ts else "PARSE FAILED"
                    window_str = "YES" if within_window else "NO"

                    print(
                        f"[{i}] {sender:20} | {ts_str:20} | In window: {window_str} | Text: {text[:50]}"
                    )

                # Test alternative selectors
                alt_selectors = [
                    "[role='article']",
                    "[data-message-id]",
                    ".message-in, .message-out",
                    "[aria-label*='Unsupported message']",
                    "div[data-pre-plain-text]",
                ]
                print("\nTesting alternative message selectors:")
                for sel in alt_selectors:
                    try:
                        found = monitor._page.query_selector_all(sel)
                        print(f"  {sel:45} -> {len(found)} elements")
                    except:
                        print(f"  {sel:45} -> ERROR")
            else:
                print(f"[!] Could not navigate to channel: {args.dump_channel}")
        finally:
            monitor._stop_browser()
        return

    monitor = WhatsAppMonitor(lookback_hours=args.hours, launch_mode=args.launch)
    messages = monitor.run()

    # Print summary
    print(f"\nMessages by channel:")
    from collections import Counter

    counts = Counter(m.channel for m in messages)
    for channel, count in counts.most_common():        print(f"  {channel}: {count}")

    # Print raw messages for inspection
    print("\nRaw messages:")
    for m in messages:
        ts = m.timestamp.strftime("%Y-%m-%d %H:%M") if m.timestamp else "?"
        print(f"  [{m.channel}] {ts} {m.sender}: {m.text[:100]}")


if __name__ == "__main__":
    main()
