"""
cancellation_workflow.py — Stage 6
=====================================
Main orchestrator for the post-decision cover workflow.

Two entry points:

  1.  process_cancellation(cover_request_id)
      Admin has decided to cancel the class entirely:
        • Attempt to cancel the Momence session via API
        • Fetch booked clients from Momence
        • Send cancellation emails to all booked clients
        • Post cancellation announcement to WhatsApp channel
        • Update cover_request status → 'cancelled'
        • Log all actions to cover_notifications

  2.  process_cover_transfer(cover_request_id)
      Admin has confirmed a cover teacher:
        • Fetch booked clients from Momence
        • Send teacher-transfer emails to all booked clients
        • Post cover-confirmed announcement to WhatsApp channel
        • (Momence teacher update: manual step — API not exposed)
        • cover_request status is already 'covered' from the dashboard

Both functions accept a dry_run flag to preview all actions without
sending emails, posting to WhatsApp, or writing to Supabase.

CLI usage
---------
    python stage6/cancellation_workflow.py --request-id <uuid> --mode cancel   [--dry-run]
    python stage6/cancellation_workflow.py --request-id <uuid> --mode transfer [--dry-run]
    python stage6/cancellation_workflow.py --mode pending [--dry-run]
        # Process all approved-but-unnotified requests automatically
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# RSO Phase 3: config.py sets services/momence/ on sys.path
from config import sb_get, sb_patch, sb_post  # noqa: E402
from momence_api_client import MomenceAPIClient  # noqa: E402 (path set by config)
from stage4.notifier import (  # noqa: E402
    WhatsAppSender,
    build_confirmed_message,
    log_notification,
)
from stage6.momence_updater import (  # noqa: E402
    get_session_details,
    get_booked_clients,
    cancel_session_in_momence,
    build_session_summary,
)
from stage6.client_notifier import ClientNotifier  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Supabase data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_request(cover_request_id: str) -> dict | None:
    """Load a cover_request row with its confirmed candidate and channel info."""
    rows = sb_get('cover_requests', params={
        'cover_request_id': f'eq.{cover_request_id}',
        'select': (
            '*,'
            'whatsapp_channels(channel_name,community_name),'
            'cover_candidates(*,teachers(id,first_name,last_name,email,whatsapp_phone))'
        ),
        'limit': '1',
    })
    return rows[0] if rows else None


def _get_confirmed_candidate(request: dict) -> dict | None:
    """Return the confirmed cover_candidate row (with teacher join), or None."""
    for c in (request.get('cover_candidates') or []):
        if c.get('is_confirmed'):
            return c
    return None


def _get_primary_channel(request: dict) -> str:
    """Return the WhatsApp channel name to post announcements to."""
    ch = request.get('whatsapp_channels')
    if isinstance(ch, dict):
        return ch.get('channel_name') or ''
    return ''


def _load_pending_requests(mode: str) -> list[dict]:
    """
    Load cover_requests needing Stage 6 processing.
    mode='cancel'   → status = 'cancelled', client_notified IS NULL / false
    mode='transfer' → status = 'covered',   client_notified IS NULL / false
    """
    status = 'cancelled' if mode == 'cancel' else 'covered'
    # We use admin_notes as a proxy for 'notified' until a dedicated column exists.
    # Requests already processed will have admin_notes containing '[S6:'
    rows = sb_get('cover_requests', params={
        'status': f'eq.{status}',
        'select': (
            '*,'
            'whatsapp_channels(channel_name,community_name),'
            'cover_candidates(*,teachers(id,first_name,last_name,email,whatsapp_phone))'
        ),
        'order': 'class_date.asc,class_time.asc',
    })
    # Filter out already-processed
    return [r for r in rows if '[S6:' not in (r.get('admin_notes') or '')]


# ─────────────────────────────────────────────────────────────────────────────
# WhatsApp announcement helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_cancellation_wa_message(request: dict, summary: dict) -> str:
    class_name = summary['class_name']
    date_str   = summary['session_date']
    time_str   = summary['session_time']
    studio     = summary['studio']
    teacher    = summary['teacher_name']
    return (
        f'⚠️ CLASS CANCELLED\n\n'
        f'Unfortunately the following class has been cancelled:\n\n'
        f'Class:   {class_name}\n'
        f'Date:    {date_str}\n'
        f'Time:    {time_str}\n'
        f'Studio:  {studio}\n'
        f'Teacher: {teacher}\n\n'
        f'Booked clients have been notified by email.\n'
        f'We apologise for the inconvenience. 🙏'
    )


def _build_transfer_wa_message(request: dict, summary: dict, cover_name: str) -> str:
    class_name = summary['class_name']
    date_str   = summary['session_date']
    time_str   = summary['session_time']
    studio     = summary['studio']
    original   = summary['teacher_name']
    return (
        f'✅ COVER CONFIRMED\n\n'
        f'Class:         {class_name}\n'
        f'Date:          {date_str}\n'
        f'Time:          {time_str}\n'
        f'Studio:        {studio}\n'
        f'Cover teacher: {cover_name}\n'
        f'Covering for:  {original}\n\n'
        f'Booked clients have been notified. Thank you {cover_name}! 🙏'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mark request as Stage 6 processed
# ─────────────────────────────────────────────────────────────────────────────

def _stamp_processed(request: dict, summary_note: str, dry_run: bool) -> None:
    """
    Append a processing stamp to admin_notes so we do not re-process.
    Format: ' [S6: <timestamp> — <summary>]'
    """
    if dry_run:
        return
    existing = request.get('admin_notes') or ''
    stamp    = f' [S6: {datetime.now().strftime("%Y-%m-%d %H:%M")} — {summary_note}]'
    new_notes = (existing + stamp).strip()
    try:
        sb_patch('cover_requests',
                 {'admin_notes': new_notes},
                 {'cover_request_id': f'eq.{request["cover_request_id"]}'})
    except Exception as e:
        print(f'  Warning: could not stamp admin_notes: {e}')


# ─────────────────────────────────────────────────────────────────────────────
# Core workflows
# ─────────────────────────────────────────────────────────────────────────────

def process_cancellation(
    cover_request_id: str,
    dry_run: bool = False,
) -> dict:
    """
    Full cancellation workflow for a single cover_request.

    Returns a summary dict with counts and any manual action notes.
    """
    mode_tag = '[DRY RUN] ' if dry_run else ''
    print(f'\n{"="*60}')
    print(f'{mode_tag}Stage 6 — Class Cancellation')
    print(f'Request ID: {cover_request_id}')
    print('='*60)

    # ── 1. Load cover request ──────────────────────────────────────────────
    request = _load_request(cover_request_id)
    if not request:
        print('  ERROR: cover_request not found in Supabase.')
        return {'error': 'request_not_found'}

    session_id  = request.get('momence_session_id')
    channel     = _get_primary_channel(request)
    manual_actions: list[str] = []

    # ── 2. Connect to Momence ──────────────────────────────────────────────
    print('\nConnecting to Momence API...')
    client = MomenceAPIClient()
    client.authenticate()

    # ── 3. Fetch session details ───────────────────────────────────────────
    session = None
    if session_id:
        print(f'  Fetching session {session_id}...')
        session = get_session_details(client, session_id)
        if not session:
            print(f'  Warning: session {session_id} not found in Momence.')
            manual_actions.append(f'Verify session {session_id} in Momence admin.')
    else:
        print('  No momence_session_id on request — using cover_request fields only.')
        manual_actions.append(
            'No Momence session ID linked. '
            'Manually cancel the session in the Momence admin portal.'
        )

    summary = build_session_summary(session, request)
    print(f'  Class: {summary["class_name"]} | {summary["session_date"]} {summary["session_time"]} | {summary["studio"]}')

    # ── 4. Attempt Momence session cancellation ────────────────────────────
    if session_id and not dry_run:
        print(f'\n  Attempting Momence API cancellation for session {session_id}...')
        ok, msg = cancel_session_in_momence(client, session_id)
        if ok:
            print(f'  ✓ Momence session cancelled via API.')
        else:
            print(f'  ⚠  Momence API cancellation not available ({msg}).')
            manual_actions.append(
                f'Manually cancel session {session_id} in the Momence admin portal '
                f'to trigger automatic client refunds/credits.'
            )
    elif session_id and dry_run:
        print(f'\n  [DRY RUN] Would attempt Momence API cancellation for session {session_id}.')

    # ── 5. Fetch booked clients ────────────────────────────────────────────
    clients: list[dict] = []
    if session_id:
        print(f'\n  Fetching booked clients for session {session_id}...')
        clients = get_booked_clients(client, session_id)
    else:
        print('  Skipping client fetch — no session ID.')
        manual_actions.append(
            'No session ID: manually identify and notify booked clients via Momence.'
        )
    # ── 6. Send cancellation emails to clients ────────────────────────────
    notifier = ClientNotifier(dry_run=dry_run)
    email_result = {'total': 0, 'emailed': 0, 'skipped_no_email': 0, 'failed': 0, 'dry_run': dry_run}
    if clients:
        print(f'\n  Sending cancellation emails to {len(clients)} client(s)...')
        email_result = notifier.notify_cancellation(clients, request, summary)
    else:
        print('  No clients to notify.')

    # ── 7. Post to WhatsApp channel ────────────────────────────────────────
    wa_sent = False
    if channel:
        wa_msg = _build_cancellation_wa_message(request, summary)
        print(f'\n  Posting cancellation to WhatsApp channel: {channel}')
        if dry_run:
            print(f'  [DRY RUN] Would post:\n{wa_msg}')
            wa_sent = True
        else:
            try:
                with WhatsAppSender() as wa:
                    wa_sent = wa.send_to_channel(channel, wa_msg)
                status_str = '✓' if wa_sent else '✗'
                print(f'  {status_str} WhatsApp post')
                log_notification(
                    cover_request_id, 'cancellation', 'whatsapp_channel',
                    'teacher', channel, wa_msg, None, wa_sent,
                    '' if wa_sent else 'send_failed'
                )
            except Exception as e:
                print(f'  ⚠  WhatsApp post failed: {e}')
                manual_actions.append(f'Manually post cancellation to WhatsApp channel "{channel}".')
    else:
        print('  No WhatsApp channel configured — skipping channel post.')
        manual_actions.append('Manually post cancellation notice to relevant WhatsApp channel(s).')

    # ── 8. Stamp as processed ─────────────────────────────────────────────
    note = (f'cancelled: {len(clients)} clients notified, '
            f'WA {"sent" if wa_sent else "manual"}')
    _stamp_processed(request, note, dry_run)

    # ── 9. Summary ─────────────────────────────────────────────────────────
    print(f'\n{"─"*60}')
    print(f'{mode_tag}Cancellation workflow complete.')
    print(f'  Clients notified:    {email_result["emailed"]}')
    print(f'  Skipped (no email):  {email_result["skipped_no_email"]}')
    print(f'  Email failures:      {email_result["failed"]}')
    print(f'  WhatsApp posted:     {"Yes" if wa_sent else "No"}')
    if manual_actions:
        print('\n  ⚠  MANUAL ACTIONS REQUIRED:')
        for i, action in enumerate(manual_actions, 1):
            print(f'  {i}. {action}')

    return {
        'mode':           'cancellation',
        'request_id':     cover_request_id,
        'email_result':   email_result,
        'wa_sent':        wa_sent,
        'manual_actions': manual_actions,
        'dry_run':        dry_run,
    }


def process_cover_transfer(
    cover_request_id: str,
    dry_run: bool = False,
) -> dict:
    """
    Cover-transfer notification workflow: a cover teacher has been confirmed.
    Notifies booked clients of the teacher change and posts to WhatsApp.

    Returns a summary dict.
    """
    mode_tag = '[DRY RUN] ' if dry_run else ''
    print(f'\n{"="*60}')
    print(f'{mode_tag}Stage 6 — Cover Transfer Notification')
    print(f'Request ID: {cover_request_id}')
    print('='*60)

    # ── 1. Load cover request ──────────────────────────────────────────────
    request = _load_request(cover_request_id)
    if not request:
        print('  ERROR: cover_request not found in Supabase.')
        return {'error': 'request_not_found'}

    session_id = request.get('momence_session_id')
    channel    = _get_primary_channel(request)
    confirmed  = _get_confirmed_candidate(request)
    manual_actions: list[str] = []

    # Resolve cover teacher name
    if confirmed:
        t = confirmed.get('teachers') or {}
        cover_name = f"{t.get('first_name','')} {t.get('last_name','')}".strip()
    else:
        cover_name = 'your cover teacher'
        print('  Warning: no confirmed candidate found on this request.')
        manual_actions.append(
            'No confirmed candidate in Supabase. '
            'Confirm a candidate in the dashboard before re-running.'
        )

    # ── 2. Connect to Momence ──────────────────────────────────────────────
    print('\nConnecting to Momence API...')
    client = MomenceAPIClient()
    client.authenticate()

    # ── 3. Fetch session details ───────────────────────────────────────────
    session = None
    if session_id:
        print(f'  Fetching session {session_id}...')
        session = get_session_details(client, session_id)
        if not session:
            print(f'  Warning: session {session_id} not found in Momence.')
            manual_actions.append(
                f'Update teacher on session {session_id} in the Momence admin portal.'
            )
    else:
        manual_actions.append(
            'No Momence session ID: manually update the teacher in the Momence admin portal.'
        )

    summary = build_session_summary(session, request)
    print(f'  Class: {summary["class_name"]} | {summary["session_date"]} {summary["session_time"]} | {summary["studio"]}')
    print(f'  Cover teacher: {cover_name}')

    # ── 4. Note: Momence teacher update requires manual step ──────────────
    if session_id:
        manual_actions.append(
            f'Update the teacher on Momence session {session_id} to '
            f'"{cover_name}" in the Momence admin portal.'
        )

    # ── 5. Fetch booked clients ────────────────────────────────────────────
    clients: list[dict] = []
    if session_id:
        print(f'\n  Fetching booked clients for session {session_id}...')
        clients = get_booked_clients(client, session_id)
    else:
        print('  Skipping client fetch — no session ID.')

    # ── 6. Send transfer emails to clients ────────────────────────────────
    notifier = ClientNotifier(dry_run=dry_run)
    email_result = {'total': 0, 'emailed': 0, 'skipped_no_email': 0, 'failed': 0, 'dry_run': dry_run}
    if clients and cover_name != 'your cover teacher':
        print(f'\n  Sending transfer emails to {len(clients)} client(s)...')
        email_result = notifier.notify_transfer(clients, request, summary, cover_name)
    elif not clients:
        print('  No clients to notify.')
    else:
        print('  Skipping client emails — cover teacher name not confirmed.')

    # ── 7. Post to WhatsApp channel ────────────────────────────────────────
    wa_sent = False
    if channel:
        wa_msg = _build_transfer_wa_message(request, summary, cover_name)
        print(f'\n  Posting cover confirmation to WhatsApp channel: {channel}')
        if dry_run:
            print(f'  [DRY RUN] Would post:\n{wa_msg}')
            wa_sent = True
        else:
            try:
                with WhatsAppSender() as wa:
                    wa_sent = wa.send_to_channel(channel, wa_msg)
                status_str = '✓' if wa_sent else '✗'
                print(f'  {status_str} WhatsApp post')
                log_notification(
                    cover_request_id, 'cover_confirmed', 'whatsapp_channel',
                    'teacher', channel, wa_msg, None, wa_sent,
                    '' if wa_sent else 'send_failed'
                )
            except Exception as e:
                print(f'  ⚠  WhatsApp post failed: {e}')
                manual_actions.append(f'Manually post cover confirmation to WhatsApp channel "{channel}".')
    else:
        print('  No WhatsApp channel configured — skipping channel post.')
        manual_actions.append('Manually post cover confirmation to relevant WhatsApp channel(s).')

    # ── 8. Stamp as processed ─────────────────────────────────────────────
    note = (f'transfer to {cover_name}: {len(clients)} clients notified, '
            f'WA {"sent" if wa_sent else "manual"}')
    _stamp_processed(request, note, dry_run)

    # ── 9. Summary ─────────────────────────────────────────────────────────
    print(f'\n{"─"*60}')
    print(f'{mode_tag}Transfer notification workflow complete.')
    print(f'  Cover teacher:       {cover_name}')
    print(f'  Clients notified:    {email_result["emailed"]}')
    print(f'  Skipped (no email):  {email_result["skipped_no_email"]}')
    print(f'  Email failures:      {email_result["failed"]}')
    print(f'  WhatsApp posted:     {"Yes" if wa_sent else "No"}')
    if manual_actions:
        print('\n  ⚠  MANUAL ACTIONS REQUIRED:')
        for i, action in enumerate(manual_actions, 1):
            print(f'  {i}. {action}')

    return {
        'mode':           'transfer',
        'request_id':     cover_request_id,
        'cover_teacher':  cover_name,
        'email_result':   email_result,
        'wa_sent':        wa_sent,
        'manual_actions': manual_actions,
        'dry_run':        dry_run,
    }


def process_pending(dry_run: bool = False) -> None:
    """
    Process all unnotified cancelled and covered requests automatically.
    Useful for a scheduled run after the admin has resolved requests in the dashboard.
    """
    print(f'\n{"="*60}')
    print(f'Stage 6 — Batch processing pending notifications')
    print('='*60)

    cancellations = _load_pending_requests('cancel')
    transfers     = _load_pending_requests('transfer')

    print(f'  Pending cancellations: {len(cancellations)}')
    print(f'  Pending transfers:     {len(transfers)}')

    for r in cancellations:
        process_cancellation(r['cover_request_id'], dry_run=dry_run)

    for r in transfers:
        process_cover_transfer(r['cover_request_id'], dry_run=dry_run)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Stage 6: Cancellation & client notification workflow'
    )
    parser.add_argument(
        '--request-id', metavar='UUID',
        help='cover_request_id to process (required for --mode cancel or transfer)'
    )
    parser.add_argument(
        '--mode', choices=['cancel', 'transfer', 'pending'], required=True,
        help=(
            'cancel   — class is cancelled; notify clients and post to WhatsApp\n'
            'transfer — cover confirmed; notify clients of teacher change\n'
            'pending  — process all unnotified cancelled/covered requests'
        )
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview all actions without sending emails, posting to WhatsApp, or writing to Supabase'
    )
    args = parser.parse_args()

    if args.mode == 'pending':
        process_pending(dry_run=args.dry_run)
    elif not args.request_id:
        parser.error('--request-id is required for --mode cancel and --mode transfer')
    elif args.mode == 'cancel':
        result = process_cancellation(args.request_id, dry_run=args.dry_run)
        print('\nResult:', json.dumps(result, indent=2, default=str))
    else:
        result = process_cover_transfer(args.request_id, dry_run=args.dry_run)
        print('\nResult:', json.dumps(result, indent=2, default=str))
