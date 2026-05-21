"""
client_notifier.py — Stage 6
==============================
Builds and sends client-facing notification emails for two scenarios:

  1.  Class Cancellation  — the class will not proceed; booked clients are
                            notified and encouraged to rebook.
  2.  Class Transfer      — a cover teacher has been confirmed; booked
                            clients are notified of the change.

All sent emails are logged to the cover_notifications Supabase table.

Environment variables (same as stage4/notifier.py):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
  NOTIFY_FROM, NOTIFY_REPLY_TO
  STUDIO_WEBSITE  — linked in client emails (optional)
  STUDIO_PHONE    — shown in client emails (optional)

Usage
-----
    from stage6.client_notifier import ClientNotifier

    notifier = ClientNotifier(dry_run=True)
    result = notifier.notify_cancellation(clients, request, session_summary)
    result = notifier.notify_transfer(clients, request, session_summary, cover_teacher_name)
"""

import os
import sys
import smtplib
import time as time_mod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SUPABASE_URL, SUPABASE_KEY, sb_post  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# SMTP / branding config
# ─────────────────────────────────────────────────────────────────────────────

SMTP_HOST       = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT       = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER       = os.getenv('SMTP_USER', '')
SMTP_PASSWORD   = os.getenv('SMTP_PASSWORD', '')
NOTIFY_FROM     = os.getenv('NOTIFY_FROM', f'Ritual Studios <{SMTP_USER}>')
NOTIFY_REPLY_TO = os.getenv('NOTIFY_REPLY_TO', SMTP_USER)

STUDIO_WEBSITE  = os.getenv('STUDIO_WEBSITE', 'https://www.ritualstudios.com.au')
STUDIO_PHONE    = os.getenv('STUDIO_PHONE', '')
STUDIO_NAME     = os.getenv('STUDIO_NAME', 'Ritual Studios')

# Seconds to wait between sends (avoid SMTP rate limits)
SEND_DELAY_SECONDS = float(os.getenv('CLIENT_EMAIL_DELAY', '0.5'))


# ─────────────────────────────────────────────────────────────────────────────
# Email templates
# ─────────────────────────────────────────────────────────────────────────────

_EMAIL_STYLE = """
  body { font-family: Arial, sans-serif; color: #1a1a1a; background: #f4f6f8; margin: 0; padding: 0; }
  .wrap { max-width: 560px; margin: 32px auto; background: #fff;
          border-radius: 10px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .header { background: #2D5016; color: #fff; padding: 24px 32px; }
  .header h1 { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.01em; }
  .header p  { margin: 4px 0 0; font-size: 13px; opacity: 0.75; }
  .body   { padding: 28px 32px; }
  .body p { line-height: 1.6; margin: 0 0 14px; }
  .info-table { border-collapse: collapse; width: 100%; margin: 18px 0; font-size: 14px; }
  .info-table td { padding: 7px 12px 7px 0; vertical-align: top; }
  .info-table td:first-child { font-weight: 600; width: 120px; color: #4A7C59; }
  .footer { background: #f4f6f8; padding: 16px 32px; font-size: 12px; color: #6B7280;
            border-top: 1px solid #E2E8F0; }
  .footer a { color: #4A7C59; text-decoration: none; }
"""


def _cancellation_html(client: dict, summary: dict) -> str:
    greeting = f"Hi {client.get('first_name') or 'there'},"
    contact_line = ''
    if STUDIO_PHONE:
        contact_line = f' or call us on <a href="tel:{STUDIO_PHONE}">{STUDIO_PHONE}</a>'

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_EMAIL_STYLE}</style></head><body>
<div class="wrap">
  <div class="header">
    <h1>{STUDIO_NAME}</h1>
    <p>Class Cancellation Notice</p>
  </div>
  <div class="body">
    <p>{greeting}</p>
    <p>We're sorry to let you know that the following class has been
    <strong>cancelled</strong>:</p>
    <table class="info-table">
      <tr><td>Class</td>   <td>{summary['class_name']}</td></tr>
      <tr><td>Date</td>    <td>{summary['session_date']}</td></tr>
      <tr><td>Time</td>    <td>{summary['session_time']}</td></tr>
      <tr><td>Studio</td>  <td>{summary['studio']}</td></tr>
    </table>
    <p>We apologise for any inconvenience. Please
    <a href="{STUDIO_WEBSITE}">visit our website</a>{contact_line}
    to book into another class.</p>
    <p>Thank you for your understanding, and we look forward to seeing
    you on the mat soon!</p>
    <p>Warm regards,<br><strong>{STUDIO_NAME}</strong></p>
  </div>
  <div class="footer">
    You are receiving this because you were booked into this class.
    &nbsp;|&nbsp; <a href="{STUDIO_WEBSITE}">{STUDIO_WEBSITE}</a>
  </div>
</div>
</body></html>"""


def _transfer_html(client: dict, summary: dict, cover_teacher: str) -> str:
    greeting = f"Hi {client.get('first_name') or 'there'},"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{_EMAIL_STYLE}</style></head><body>
<div class="wrap">
  <div class="header">
    <h1>{STUDIO_NAME}</h1>
    <p>Class Update — Teacher Change</p>
  </div>
  <div class="body">
    <p>{greeting}</p>
    <p>We wanted to let you know of a small change to your upcoming class:</p>
    <table class="info-table">
      <tr><td>Class</td>          <td>{summary['class_name']}</td></tr>
      <tr><td>Date</td>           <td>{summary['session_date']}</td></tr>
      <tr><td>Time</td>           <td>{summary['session_time']}</td></tr>
      <tr><td>Studio</td>         <td>{summary['studio']}</td></tr>
      <tr><td>Teacher</td>        <td><strong>{cover_teacher}</strong>
                                    (covering for {summary['teacher_name']})</td></tr>
    </table>
    <p>Your booking is secure — no action is needed on your part.
    We look forward to seeing you in class!</p>
    <p>Warm regards,<br><strong>{STUDIO_NAME}</strong></p>
  </div>
  <div class="footer">
    You are receiving this because you have a booking for this class.
    &nbsp;|&nbsp; <a href="{STUDIO_WEBSITE}">{STUDIO_WEBSITE}</a>
  </div>
</div>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# SMTP helper
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(to_address: str, subject: str, html_body: str) -> bool:
    """Send an HTML email via SMTP. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f'    Email skipped — SMTP_USER / SMTP_PASSWORD not configured.')
        return False
    if not to_address:
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
        print(f'    SMTP error for {to_address}: {e}')
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Notification log
# ─────────────────────────────────────────────────────────────────────────────

def _log_notification(
    cover_request_id: str,
    notification_type: str,
    recipient_email: str,
    message_summary: str,
    delivered: bool | None,
    delivery_notes: str = '',
) -> None:
    """Log a client notification to the cover_notifications table."""
    payload = {
        'cover_request_id':     cover_request_id,
        'cover_candidate_id':   None,
        'notification_type':    'cancellation',  # schema enum
        'channel':              'email',
        'recipient_type':       'client',
        'recipient_identifier': recipient_email,
        'message_body':         message_summary,
        'sent_at':              datetime.now(timezone.utc).isoformat(),
        'delivered':            delivered,
        'delivery_notes':       delivery_notes or None,
    }
    # Override notification_type based on actual type passed
    if notification_type == 'class_transfer':
        payload['notification_type'] = 'class_transfer'

    try:
        sb_post('cover_notifications', payload)
    except Exception as e:
        print(f'    Warning: could not log notification: {e}')


# ─────────────────────────────────────────────────────────────────────────────
# ClientNotifier
# ─────────────────────────────────────────────────────────────────────────────

class ClientNotifier:
    """
    Builds and sends client-facing emails for cancellation or cover transfer.

    Parameters
    ----------
    dry_run : bool
        If True, prints what would be sent but does not send or log.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def notify_cancellation(
        self,
        clients: list[dict],
        request: dict,
        session_summary: dict,
    ) -> dict:
        """
        Send cancellation emails to all booked clients.

        Returns a result dict:
            { total, emailed, skipped_no_email, failed, dry_run }
        """
        return self._notify_batch(
            clients=clients,
            request=request,
            session_summary=session_summary,
            notification_type='cancellation',
            cover_teacher_name=None,
        )

    def notify_transfer(
        self,
        clients: list[dict],
        request: dict,
        session_summary: dict,
        cover_teacher_name: str,
    ) -> dict:
        """
        Send teacher-transfer emails to all booked clients.

        Returns the same result dict as notify_cancellation.
        """
        return self._notify_batch(
            clients=clients,
            request=request,
            session_summary=session_summary,
            notification_type='class_transfer',
            cover_teacher_name=cover_teacher_name,
        )

    def _notify_batch(
        self,
        clients: list[dict],
        request: dict,
        session_summary: dict,
        notification_type: str,
        cover_teacher_name: str | None,
    ) -> dict:
        req_id = request.get('cover_request_id', '')
        total  = len(clients)
        emailed = skipped = failed = 0

        class_name = session_summary.get('class_name', 'class')
        date_str   = session_summary.get('session_date', '')

        if notification_type == 'cancellation':
            subject_tpl = f'[{STUDIO_NAME}] Cancellation: {class_name} — {date_str}'
        else:
            subject_tpl = f'[{STUDIO_NAME}] Class update: {class_name} — {date_str}'

        print(f'\n  Notifying {total} client(s) — type: {notification_type}')

        for c in clients:
            email = c.get('email')
            name  = c.get('full_name') or c.get('first_name') or 'client'

            if not email:
                print(f'    ⚠  {name}: no email address — skipped')
                skipped += 1
                continue

            # Build email body
            if notification_type == 'cancellation':
                html = _cancellation_html(c, session_summary)
            else:
                html = _transfer_html(c, session_summary, cover_teacher_name or 'a cover teacher')

            if self.dry_run:
                print(f'    [DRY RUN] → {email}: {subject_tpl}')
                emailed += 1
                continue

            # Send
            ok = _send_email(email, subject_tpl, html)
            if ok:
                print(f'    ✓  {email} ({name})')
                emailed += 1
                _log_notification(
                    req_id, notification_type, email,
                    f'Subject: {subject_tpl}', True
                )
            else:
                print(f'    ✗  {email} ({name}) — send failed')
                failed += 1
                _log_notification(
                    req_id, notification_type, email,
                    f'Subject: {subject_tpl}', False, 'smtp_failed'
                )

            if SEND_DELAY_SECONDS > 0:
                time_mod.sleep(SEND_DELAY_SECONDS)

        result = {
            'total':             total,
            'emailed':           emailed,
            'skipped_no_email':  skipped,
            'failed':            failed,
            'dry_run':           self.dry_run,
        }
        tag = '[DRY RUN] ' if self.dry_run else ''
        print(
            f'\n  {tag}Client notifications: '
            f'{emailed} sent, {skipped} skipped (no email), {failed} failed'
        )
        return result
