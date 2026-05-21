"""
notifier.py — Stage 4
======================
Sends cover notifications via three channels:

  1.  WhatsApp channel post  — posts to a monitored community channel
                               via WhatsApp Web / Playwright
  2.  WhatsApp direct DM     — sends a private message to the teacher's
                               whatsapp_phone via WhatsApp Web
  3.  Email                  — sends via SMTP (configured in .env)

All sent notifications are logged to the cover_notifications table.

Environment variables (in addition to those in .env.example):
  SMTP_HOST       — e.g. smtp.gmail.com
  SMTP_PORT       — e.g. 587
  SMTP_USER       — sender email address
  SMTP_PASSWORD   — app password or SMTP password
  NOTIFY_FROM     — display name + address, e.g. "Ritual Studios <hello@ritual.com>"
  NOTIFY_REPLY_TO — admin reply-to address

Usage
-----
    from notifier import Notifier, NotificationRequest
    n = Notifier()
    n.send_opportunity(cover_request, candidate)
    n.send_confirmed(cover_request, candidate)
    n.send_no_longer_needed(cover_request, candidates_list)
"""

import os
import sys
import smtplib
import time as time_mod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, time, timezone
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    SUPABASE_URL, SUPABASE_KEY,
    CHROME_DEBUG_PORT, WHATSAPP_WEB_URL,
    sb_post, sb_get
)

# ─────────────────────────────────────────────────────────────────────────────
# SMTP configuration
# ─────────────────────────────────────────────────────────────────────────────

SMTP_HOST     = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER     = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
NOTIFY_FROM   = os.getenv('NOTIFY_FROM', f'Ritual Studios <{SMTP_USER}>')
NOTIFY_REPLY_TO = os.getenv('NOTIFY_REPLY_TO', SMTP_USER)

# Playwright timeouts (ms)
PAGE_LOAD_TIMEOUT = 60_000
ELEMENT_TIMEOUT   = 15_000

# WhatsApp Web DOM selectors (update if WhatsApp changes its DOM)
SEL_SEARCH_BOX  = 'div[contenteditable="true"][data-tab="3"]'
SEL_MSG_BOX     = 'div[contenteditable="true"][data-tab="10"]'
SEL_SEND_BTN    = 'button[data-testid="send"], span[data-testid="send"]'
SEL_CHAT_ITEM   = 'div[role="listitem"]'


# ─────────────────────────────────────────────────────────────────────────────
# Message template helpers
# ─────────────────────────────────────────────────────────────────────────────

def fmt_date(d: str | None) -> str:
    """Format a YYYY-MM-DD string as 'Wednesday 9 April 2026'."""
    if not d:
        return 'TBC'
    try:
        return date.fromisoformat(d).strftime('%A %-d %B %Y')
    except (ValueError, AttributeError):
        return d


def fmt_time(t: str | None) -> str:
    """Format a HH:MM:SS time string as '5:45am'."""
    if not t:
        return 'TBC'
    try:
        return time.fromisoformat(t).strftime('%-I:%M%p').lower()
    except (ValueError, AttributeError):
        return t


def fmt_time_range(start: str | None, end: str | None) -> str:
    s = fmt_time(start)
    e = fmt_time(end)
    if end:
        return f'{s}–{e}'
    return s


def build_opportunity_message(request: dict, teacher_name: str | None = None) -> str:
    """Build the cover opportunity message text."""
    class_name = (
        request.get('class_name_raw') or
        request.get('discipline_code') or
        'class'
    ).title()
    date_str = fmt_date(request.get('class_date'))
    time_str = fmt_time_range(request.get('class_time'), request.get('class_end_time'))
    studio   = request.get('studio') or 'TBC'
    covering_for = teacher_name or request.get('requesting_teacher_name_raw') or 'a teacher'

    return (
        f'🔔 COVER NEEDED\n\n'
        f'Class:   {class_name}\n'
        f'Date:    {date_str}\n'
        f'Time:    {time_str}\n'
        f'Studio:  {studio}\n'
        f'Covering for: {covering_for}\n\n'
        f'If you are available and happy to cover this class, please '
        f'reply here or DM the coordinator. Thank you! 🙏'
    )


def build_confirmed_message(request: dict, confirmed_teacher_name: str) -> str:
    class_name = (request.get('class_name_raw') or request.get('discipline_code') or 'class').title()
    date_str   = fmt_date(request.get('class_date'))
    time_str   = fmt_time_range(request.get('class_time'), request.get('class_end_time'))
    studio     = request.get('studio') or 'TBC'
    return (
        f'✅ COVER CONFIRMED\n\n'
        f'Class:   {class_name}\n'
        f'Date:    {date_str}\n'
        f'Time:    {time_str}\n'
        f'Studio:  {studio}\n'
        f'Covered by: {confirmed_teacher_name}\n\n'
        f'Thank you {confirmed_teacher_name}! 🙏'
    )


def build_no_longer_needed_message(request: dict) -> str:
    class_name = (request.get('class_name_raw') or request.get('discipline_code') or 'class').title()
    date_str   = fmt_date(request.get('class_date'))
    time_str   = fmt_time(request.get('class_time'))
    return (
        f'ℹ️ COVER NO LONGER NEEDED\n\n'
        f'The cover request for {class_name} on {date_str} at {time_str} '
        f'has been filled or cancelled. Thank you for your availability! 🙏'
    )


def build_opportunity_email(request: dict, teacher_name: str | None,
                              recipient_name: str) -> tuple[str, str]:
    """Returns (subject, html_body) for a cover opportunity email."""
    class_name = (request.get('class_name_raw') or request.get('discipline_code') or 'class').title()
    date_str   = fmt_date(request.get('class_date'))
    time_str   = fmt_time_range(request.get('class_time'), request.get('class_end_time'))
    studio     = request.get('studio') or 'TBC'
    covering   = teacher_name or request.get('requesting_teacher_name_raw') or 'a teacher'

    subject = f'Cover needed: {class_name} — {date_str}'
    body = f"""
<p>Hi {recipient_name},</p>
<p>A cover is needed for the following class:</p>
<table style="border-collapse:collapse;font-family:Arial,sans-serif;">
  <tr><td style="padding:4px 12px 4px 0;font-weight:bold;">Class</td>
      <td style="padding:4px 0;">{class_name}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;font-weight:bold;">Date</td>
      <td style="padding:4px 0;">{date_str}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;font-weight:bold;">Time</td>
      <td style="padding:4px 0;">{time_str}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;font-weight:bold;">Studio</td>
      <td style="padding:4px 0;">{studio}</td></tr>
  <tr><td style="padding:4px 12px 4px 0;font-weight:bold;">Covering for</td>
      <td style="padding:4px 0;">{covering}</td></tr>
</table>
<p>If you are available to cover this class, please reply to this email
or contact the studio coordinator directly.</p>
<p>Thank you!</p>
<p style="color:#888;font-size:0.85em;">Ritual Studios Cover Management</p>
"""
    return subject, body


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp Web sender (Playwright)
# ─────────────────────────────────────────────────────────────────────────────

class WhatsAppSender:
    """
    Sends messages via WhatsApp Web in an existing Chrome session.
    Attach mode only (connects to chrome --remote-debugging-port=NNNN).
    """

    def __init__(self):
        self._playwright = None
        self._browser    = None
        self._page       = None

    def _connect(self) -> None:
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        try:
            self._browser = self._playwright.chromium.connect_over_cdp(
                f'http://localhost:{CHROME_DEBUG_PORT}'
            )
        except Exception as e:
            self._playwright.stop()
            raise RuntimeError(
                f'Cannot connect to Chrome on port {CHROME_DEBUG_PORT}. '
                f'Start Chrome with --remote-debugging-port={CHROME_DEBUG_PORT}. '
                f'Error: {e}'
            )
        ctx = self._browser.contexts[0]
        wa_pages = [p for p in ctx.pages if 'web.whatsapp.com' in p.url]
        if wa_pages:
            self._page = wa_pages[0]
        else:
            self._page = ctx.new_page()
            self._page.goto(WHATSAPP_WEB_URL, timeout=PAGE_LOAD_TIMEOUT)

        self._page.wait_for_selector('#pane-side', timeout=PAGE_LOAD_TIMEOUT)

    def _disconnect(self) -> None:
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    def _open_chat(self, chat_name: str) -> bool:
        """Navigate to a chat (channel or DM) by name. Returns True if found."""
        page = self._page
        try:
            search = page.wait_for_selector(SEL_SEARCH_BOX, timeout=ELEMENT_TIMEOUT)
            search.click()
            search.fill('')
            page.keyboard.type(chat_name, delay=50)
            time_mod.sleep(1.5)

            items = page.query_selector_all(SEL_CHAT_ITEM)
            for item in items:
                title_el = item.query_selector('span[title]')
                if title_el and title_el.get_attribute('title', '').strip().lower() == chat_name.lower():
                    item.click()
                    time_mod.sleep(1.0)
                    search.fill('')
                    search.press('Escape')
                    return True

            search.fill('')
            search.press('Escape')
        except Exception as e:
            print(f'    _open_chat error: {e}')
        return False

    def send_to_channel(self, channel_name: str, message: str) -> bool:
        """Post a message to a WhatsApp community channel."""
        if not self._page:
            self._connect()
        if not self._open_chat(channel_name):
            print(f'    Channel not found: {channel_name}')
            return False
        return self._send_message(message)

    def send_direct(self, phone: str, message: str) -> bool:
        """
        Open a direct chat to a phone number and send a message.
        Uses the wa.me deep-link approach which is reliable in WhatsApp Web.
        """
        if not self._page:
            self._connect()
        clean_phone = ''.join(c for c in phone if c.isdigit())
        try:
            self._page.goto(
                f'https://web.whatsapp.com/send?phone={clean_phone}',
                timeout=PAGE_LOAD_TIMEOUT
            )
            self._page.wait_for_selector(SEL_MSG_BOX, timeout=PAGE_LOAD_TIMEOUT)
            time_mod.sleep(1.5)
            return self._send_message(message)
        except Exception as e:
            print(f'    Direct send error: {e}')
            return False

    def _send_message(self, message: str) -> bool:
        """Type and send a message in the currently open chat."""
        try:
            msg_box = self._page.wait_for_selector(SEL_MSG_BOX, timeout=ELEMENT_TIMEOUT)
            msg_box.click()
            for line in message.split('\n'):
                msg_box.type(line)
                self._page.keyboard.press('Shift+Enter')
            self._page.keyboard.press('Backspace')
            time_mod.sleep(0.5)

            send_btn = self._page.query_selector(SEL_SEND_BTN)
            if send_btn:
                send_btn.click()
            else:
                self._page.keyboard.press('Enter')

            time_mod.sleep(1.0)
            return True
        except Exception as e:
            print(f'    _send_message error: {e}')
            return False

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, *_):
        self._disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# Email sender
# ─────────────────────────────────────────────────────────────────────────────

def send_email(to_address: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f'    Email skipped — SMTP_USER / SMTP_PASSWORD not configured.')
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject']  = subject
    msg['From']     = NOTIFY_FROM
    msg['To']       = to_address
    msg['Reply-To'] = NOTIFY_REPLY_TO
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_address, msg.as_string())
        return True
    except smtplib.SMTPException as e:
        print(f'    SMTP error: {e}')
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Notification log
# ─────────────────────────────────────────────────────────────────────────────

def log_notification(
    cover_request_id: str,
    notification_type: str,
    channel: str,
    recipient_type: str,
    recipient_identifier: str,
    message_body: str,
    cover_candidate_id: str | None = None,
    delivered: bool | None = None,
    delivery_notes: str = '',
) -> str | None:
    """Insert a row into cover_notifications and return its ID."""
    payload = {
        'cover_request_id':     cover_request_id,
        'cover_candidate_id':   cover_candidate_id,
        'notification_type':    notification_type,
        'channel':              channel,
        'recipient_type':       recipient_type,
        'recipient_identifier': recipient_identifier,
        'message_body':         message_body,
        'sent_at':              datetime.now(timezone.utc).isoformat(),
        'delivered':            delivered,
        'delivery_notes':       delivery_notes or None,
    }
    try:
        rows = sb_post('cover_notifications', payload)
        return rows[0]['cover_notification_id'] if rows else None
    except Exception as e:
        print(f'    Warning: could not log notification: {e}')
        return None


# ─────────────────────────────────────────────────────────────────────────────
# High-level Notifier
# ─────────────────────────────────────────────────────────────────────────────

class Notifier:
    """
    Sends and logs cover notifications.
    Uses a single WhatsApp browser session for all WA sends in a run.
    """

    def __init__(self, wa_sender: WhatsAppSender | None = None, dry_run: bool = False):
        self._wa      = wa_sender
        self.dry_run  = dry_run

    def send_opportunity(self, request: dict, candidate, channel_name: str) -> None:
        """Notify a single candidate of a cover opportunity."""
        req_id   = request['cover_request_id']
        cand_id  = getattr(candidate, 'cover_candidate_id', None)
        msg_text = build_opportunity_message(
            request, teacher_name=request.get('requesting_teacher_name_raw')
        )

        self._send_wa_channel(channel_name, msg_text, req_id, 'cover_opportunity', cand_id)

        pref = candidate.contact_preference or 'whatsapp_channel'
        if candidate.whatsapp_phone and pref in ('whatsapp_direct', 'all'):
            dm_text = f'Hi {candidate.first_name}, {msg_text}'
            self._send_wa_direct(candidate.whatsapp_phone, dm_text, req_id, 'cover_opportunity', cand_id)

        if candidate.email and pref in ('email', 'all'):
            subject, html_body = build_opportunity_email(
                request, request.get('requesting_teacher_name_raw'), candidate.first_name,
            )
            self._send_email(candidate.email, subject, html_body, req_id, 'cover_opportunity', cand_id)

    def send_channel_opportunity(self, request: dict, channel_name: str) -> None:
        """Post a single cover opportunity message to the channel (general broadcast)."""
        msg_text = build_opportunity_message(request, request.get('requesting_teacher_name_raw'))
        self._send_wa_channel(channel_name, msg_text, request['cover_request_id'], 'cover_opportunity', None)

    def send_confirmed(self, request: dict, confirmed_candidate, channel_name: str) -> None:
        """Announce that cover has been confirmed."""
        req_id   = request['cover_request_id']
        cand_id  = getattr(confirmed_candidate, 'cover_candidate_id', None)
        msg_text = build_confirmed_message(request, confirmed_candidate.full_name)

        self._send_wa_channel(channel_name, msg_text, req_id, 'cover_confirmed', cand_id)

        if confirmed_candidate.whatsapp_phone:
            self._send_wa_direct(
                confirmed_candidate.whatsapp_phone,
                f'Hi {confirmed_candidate.first_name}, you\'re confirmed to cover: {msg_text}',
                req_id, 'cover_confirmed', cand_id
            )
        if confirmed_candidate.email:
            subject = f'Cover confirmed: {request.get("class_name_raw") or "class"}'
            html    = f'<p>Hi {confirmed_candidate.first_name},</p><p>{msg_text}</p>'
            self._send_email(confirmed_candidate.email, subject, html, req_id, 'cover_confirmed', cand_id)

    def send_no_longer_needed(self, request: dict, candidates: list) -> None:
        """Notify all non-confirmed candidates that cover is no longer needed."""
        req_id   = request['cover_request_id']
        msg_text = build_no_longer_needed_message(request)

        for c in candidates:
            if getattr(c, 'is_confirmed', False):
                continue
            cand_id = getattr(c, 'cover_candidate_id', None)
            pref = c.contact_preference or 'whatsapp_channel'

            if c.whatsapp_phone and pref in ('whatsapp_direct', 'all'):
                self._send_wa_direct(c.whatsapp_phone, f'Hi {c.first_name}, {msg_text}',
                                     req_id, 'cover_no_longer_needed', cand_id)

            if c.email and pref in ('email', 'all'):
                self._send_email(c.email, 'Cover update: no longer needed',
                                 f'<p>Hi {c.first_name},</p><p>{msg_text}</p>',
                                 req_id, 'cover_no_longer_needed', cand_id)

    def _send_wa_channel(self, channel, text, req_id, notif_type, cand_id):
        delivered, notes = None, ''
        if self.dry_run:
            print(f'    [DRY RUN] WA channel → {channel}: {text[:60]}…')
        elif self._wa:
            ok = self._wa.send_to_channel(channel, text)
            delivered = ok; notes = '' if ok else 'send_failed'
            print(f'    WA channel → {channel}: {"✓" if ok else "✗"}')
        else:
            print('    WA channel skipped (no sender configured)')
        if not self.dry_run:
            log_notification(req_id, notif_type, 'whatsapp_channel', 'teacher', channel, text, cand_id, delivered, notes)

    def _send_wa_direct(self, phone, text, req_id, notif_type, cand_id):
        delivered, notes = None, ''
        if self.dry_run:
            print(f'    [DRY RUN] WA direct → {phone}: {text[:60]}…')
        elif self._wa:
            ok = self._wa.send_direct(phone, text)
            delivered = ok; notes = '' if ok else 'send_failed'
            print(f'    WA direct → {phone}: {"✓" if ok else "✗"}')
        else:
            print('    WA direct skipped (no sender configured)')
        if not self.dry_run:
            log_notification(req_id, notif_type, 'whatsapp_direct', 'teacher', phone, text, cand_id, delivered, notes)

    def _send_email(self, to, subject, html, req_id, notif_type, cand_id):
        delivered, notes = None, ''
        if self.dry_run:
            print(f'    [DRY RUN] Email → {to}: {subject}')
        else:
            ok = send_email(to, subject, html)
            delivered = ok; notes = '' if ok else 'smtp_failed'
            print(f'    Email → {to}: {"✓" if ok else "✗"}')
        if not self.dry_run:
            log_notification(req_id, notif_type, 'email', 'teacher', to, f'Subject: {subject}', cand_id, delivered, notes)
