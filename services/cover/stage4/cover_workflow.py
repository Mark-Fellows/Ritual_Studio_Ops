"""
cover_workflow.py — Stage 4  (main entry point)
================================================
Orchestrates the full Stage 4 workflow:

  1.  Load approved cover requests from Supabase
  2.  Run teacher matching for each request
  3.  Persist cover_candidates rows
  4.  Send cover opportunity notifications (WhatsApp channel + DM + email)
  5.  Provide a response handler for when a teacher confirms

Admin controls the workflow via Supabase (setting request status to
'approved') and confirms a teacher by calling confirm_cover().

Sub-commands
------------
    python cover_workflow.py run              # process all approved requests
    python cover_workflow.py run --dry-run   # preview without sending/writing
    python cover_workflow.py confirm <request_id> <teacher_id>
                                             # confirm a specific teacher
    python cover_workflow.py expire          # mark expired requests
    python cover_workflow.py status          # print workflow summary

Notification channel
--------------------
Cover opportunity messages are posted to the first active WhatsApp channel
in whatsapp_channels that matches the request's discipline, or to the
RITUAL TEACHERS channel if no discipline-specific channel is found.
"""

import sys
import argparse
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import sb_get, sb_post, sb_patch, get_config_value
from teacher_matcher import TeacherMatcher, CandidateMatch
from notifier import Notifier, WhatsAppSender


# ─────────────────────────────────────────────────────────────────────────────
# Channel selection
# ─────────────────────────────────────────────────────────────────────────────

def pick_notify_channel(request: dict) -> str:
    """
    Choose which WhatsApp channel to post the opportunity to.

    Priority:
    1. Channel whose name contains the discipline keyword
    2. 'RITUAL TEACHERS' (general channel)
    3. First active channel
    """
    discipline = (request.get('discipline_code') or '').lower()

    channels = sb_get('whatsapp_channels', params={
        'is_active': 'eq.true',
        'order':     'monitor_order',
        'select':    'channel_name,community_name',
    })

    if not channels:
        return 'RITUAL TEACHERS'

    disc_keywords = {
        'reformer':    'reformer',
        'yin':         'yin',
        'barre':       'barre',
        'mat_pilates': 'mat pilates',
        'yoga':        'teachers',
    }
    kw = disc_keywords.get(discipline, '')

    for ch in channels:
        if kw and kw in ch['channel_name'].lower():
            return ch['channel_name']

    for ch in channels:
        if 'teachers' in ch['channel_name'].lower():
            return ch['channel_name']

    return channels[0]['channel_name']


# ─────────────────────────────────────────────────────────────────────────────
# Request loading
# ─────────────────────────────────────────────────────────────────────────────

def load_approved_requests() -> list[dict]:
    """Load cover requests with status='approved' that need candidate matching."""
    return sb_get('cover_requests', params={
        'status': 'eq.approved',
        'order':  'class_date,class_time',
        'select': (
            'cover_request_id,discipline_code,studio,class_date,'
            'class_time,class_end_time,class_name_raw,'
            'requesting_teacher_id,requesting_teacher_name_raw,'
            'confidence_score,momence_session_id'
        ),
    })


def load_candidates_for_request(cover_request_id: str) -> list[dict]:
    """Load existing candidates with their teacher details."""
    return sb_get('cover_candidates', params={
        'cover_request_id': f'eq.{cover_request_id}',
        'select': (
            'cover_candidate_id,teacher_id,match_score,matched_grade,'
            'contact_channels,contacted_at,response,is_confirmed'
        ),
        'order': 'match_score.desc',
    })


# ─────────────────────────────────────────────────────────────────────────────
# Core workflow step: match and notify
# ─────────────────────────────────────────────────────────────────────────────

def process_approved_request(
    request: dict,
    matcher: TeacherMatcher,
    notifier: Notifier,
    dry_run: bool = False,
) -> int:
    """
    Run matching + notification for one approved request.
    Returns number of candidates found.
    """
    req_id     = request['cover_request_id']
    discipline = request.get('discipline_code') or ''
    channel    = pick_notify_channel(request)

    print(f'\n  Request: {req_id}')
    print(
        f'  {request.get("class_name_raw") or discipline} | '
        f'{request.get("class_date")} {request.get("class_time")} | '
        f'{request.get("studio")}'
    )
    print(f'  Notifying via channel: {channel}')

    existing = load_candidates_for_request(req_id)
    already_contacted = {e['teacher_id'] for e in existing if e.get('contacted_at')}
    print(f'  Existing candidates: {len(existing)} ({len(already_contacted)} already contacted)')

    print('  Running teacher matching…')
    candidates = matcher.find(
        request, exclude_teacher_id=request.get('requesting_teacher_id')
    )
    print(f'  → {len(candidates)} eligible teacher(s) found')

    if not candidates:
        print('  No eligible teachers found.')
        notifier.send_channel_opportunity(request, channel)
        return 0

    inserted_ids = matcher.save_candidates(candidates, req_id, discipline, dry_run=dry_run)

    new_candidates = [c for c in candidates if c.teacher_id not in already_contacted]
    print(f'  New candidates to notify: {len(new_candidates)}')

    # Post to channel once per request (first run only)
    if not already_contacted:
        notifier.send_channel_opportunity(request, channel)

    for c in new_candidates:
        print(f'  Notifying: {c.full_name}')
        notifier.send_opportunity(request, c, channel)

        if not dry_run:
            cand_rows = sb_get('cover_candidates', params={
                'cover_request_id': f'eq.{req_id}',
                'teacher_id':       f'eq.{c.teacher_id}',
                'select':           'cover_candidate_id',
            })
            if cand_rows:
                sb_patch(
                    'cover_candidates',
                    {
                        'contacted_at':     datetime.now(timezone.utc).isoformat(),
                        'contact_channels': ['whatsapp_channel'],
                    },
                    {'cover_candidate_id': f'eq.{cand_rows[0]["cover_candidate_id"]}'}
                )

    return len(candidates)


# ─────────────────────────────────────────────────────────────────────────────
# Confirm cover
# ─────────────────────────────────────────────────────────────────────────────

def confirm_cover(cover_request_id: str, teacher_id: str, dry_run: bool = False) -> None:
    """
    Confirm a specific teacher as the cover for a request.
    - Sets cover_candidates.is_confirmed = true for that teacher
    - Sets cover_request.status = 'covered'
    - Sends cover_confirmed notification
    - Sends cover_no_longer_needed to all other candidates
    """
    print(f'\nConfirming cover: request={cover_request_id} teacher={teacher_id}')

    reqs = sb_get('cover_requests', params={
        'cover_request_id': f'eq.{cover_request_id}', 'select': '*',
    })
    if not reqs:
        print(f'  Request {cover_request_id} not found.')
        return
    request = reqs[0]

    candidates_db = load_candidates_for_request(cover_request_id)

    all_teachers = {
        t['id']: t for t in sb_get('teachers', params={
            'select': 'id,first_name,last_name,email,whatsapp_phone,contact_preference'
        })
    }

    confirmed_cand   = None
    other_candidates = []

    for c_db in candidates_db:
        t = all_teachers.get(c_db['teacher_id'])
        if not t:
            continue
        cand_obj = type('C', (), {
            'teacher_id':         t['id'],
            'first_name':         t.get('first_name', ''),
            'last_name':          t.get('last_name', ''),
            'full_name':          f'{t.get("first_name","")}{t.get("last_name","")}'.strip(),
            'email':              t.get('email'),
            'whatsapp_phone':     t.get('whatsapp_phone'),
            'contact_preference': t.get('contact_preference', 'whatsapp_channel'),
            'is_confirmed':       c_db.get('is_confirmed', False),
            'cover_candidate_id': c_db['cover_candidate_id'],
        })()

        if t['id'] == teacher_id:
            confirmed_cand = cand_obj
        else:
            other_candidates.append(cand_obj)

    if not confirmed_cand:
        print(f'  Teacher {teacher_id} is not a candidate for this request.')
        print('  Add them as a candidate first via teacher_matcher.py --save')
        return

    channel = pick_notify_channel(request)

    with WhatsAppSender() as wa:
        notif = Notifier(wa_sender=wa, dry_run=dry_run)

        print(f'\n  Sending confirmation to {confirmed_cand.full_name}…')
        notif.send_confirmed(request, confirmed_cand, channel)

        if other_candidates:
            print(f'  Sending "no longer needed" to {len(other_candidates)} other candidate(s)…')
            notif.send_no_longer_needed(request, other_candidates)

    if not dry_run:
        sb_patch(
            'cover_candidates',
            {'is_confirmed': True, 'response': 'accepted',
             'responded_at': datetime.now(timezone.utc).isoformat()},
            {'cover_candidate_id': f'eq.{confirmed_cand.cover_candidate_id}'}
        )
        sb_patch(
            'cover_requests',
            {'status': 'covered'},
            {'cover_request_id': f'eq.{cover_request_id}'}
        )
        print(f'\n  ✓ Request {cover_request_id} marked as COVERED.')
    else:
        print(f'\n  [DRY RUN] Would mark request as covered and candidate as confirmed.')


# ─────────────────────────────────────────────────────────────────────────────
# Expire stale requests
# ─────────────────────────────────────────────────────────────────────────────

def expire_stale_requests(dry_run: bool = False) -> int:
    """Mark requests as 'expired' where class_date+time is in the past."""
    stale = sb_get('cover_requests', params={
        'select': 'cover_request_id,class_date,class_time,status',
        'status': 'in.(pending_review,approved)',
    })

    expired = []
    for r in stale:
        dt_str = r.get('class_date')
        t_str  = r.get('class_time')
        if not dt_str:
            continue
        try:
            class_dt = datetime.fromisoformat(f'{dt_str}T{t_str or "00:00:00"}')
            if class_dt < datetime.now():
                expired.append(r['cover_request_id'])
        except ValueError:
            pass

    print(f'Expiring {len(expired)} stale request(s)…')
    for req_id in expired:
        if not dry_run:
            sb_patch('cover_requests', {'status': 'expired'},
                     {'cover_request_id': f'eq.{req_id}'})
        print(f'  {"[DRY RUN] " if dry_run else ""}Expired: {req_id}')

    return len(expired)


# ─────────────────────────────────────────────────────────────────────────────
# Status summary
# ─────────────────────────────────────────────────────────────────────────────

def print_status() -> None:
    """Print a summary of all cover_requests by status."""
    rows = sb_get('cover_requests', params={
        'select': 'status,class_date,class_time,studio,discipline_code,'
                  'requesting_teacher_name_raw,confidence_score,'
                  'auto_review_required,cover_request_id',
        'order':  'created_at.desc',
    })

    from collections import Counter
    counts = Counter(r['status'] for r in rows)

    print(f'\n{"="*60}')
    print(f'Cover Request Status Summary  ({datetime.now().strftime("%Y-%m-%d %H:%M")})')
    print(f'{"="*60}')
    print(f'Total requests: {len(rows)}')
    for status, count in sorted(counts.items()):
        print(f'  {status:20s}: {count}')

    print()
    pending = [r for r in rows if r['status'] in ('pending_review', 'approved')]
    if pending:
        print('Open requests:')
        print(f'  {"Status":<18} {"Date":<12} {"Time":<8} {"Studio":<12} '
              f'{"Teacher":<20} {"Conf":>5} {"Review?"}')
        print('  ' + '-' * 80)
        for r in pending:
            print(
                f'  {r["status"]:<18} '
                f'{r.get("class_date") or "?":<12} '
                f'{(r.get("class_time") or "?")[:5]:<8} '
                f'{r.get("studio") or "?":<12} '
                f'{r.get("requesting_teacher_name_raw") or "?":<20} '
                f'{float(r.get("confidence_score") or 0):>5.2f} '
                f'{"YES" if r.get("auto_review_required") else "no"}'
            )
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Main run
# ─────────────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    mode = '[DRY RUN] ' if dry_run else ''
    print(f'\n{"="*60}')
    print(f'{mode}Cover Workflow — Stage 4')
    print(f'{"="*60}\n')

    requests = load_approved_requests()
    print(f'Approved requests to process: {len(requests)}')

    if not requests:
        print('No approved requests. Exiting.')
        print(
            '\nTip: Use the Supabase dashboard to set cover_request.status '
            'from "pending_review" to "approved" after reviewing NLP output.'
        )
        return

    matcher = TeacherMatcher()
    total_candidates = 0

    with WhatsAppSender() as wa:
        notif = Notifier(wa_sender=wa, dry_run=dry_run)
        for req in requests:
            n = process_approved_request(req, matcher, notif, dry_run=dry_run)
            total_candidates += n

    expired = expire_stale_requests(dry_run=dry_run)

    print(f'\n{"="*60}')
    print(f'Workflow complete:')
    print(f'  Requests processed: {len(requests)}')
    print(f'  Candidates found:   {total_candidates}')
    print(f'  Requests expired:   {expired}')


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Stage 4: teacher matching and cover notifications'
    )
    sub = ap.add_subparsers(dest='cmd')

    run_p = sub.add_parser('run', help='Process all approved cover requests')
    run_p.add_argument('--dry-run', action='store_true',
                       help='Preview without sending notifications or writing to DB')

    conf_p = sub.add_parser('confirm', help='Confirm a specific teacher as cover')
    conf_p.add_argument('request_id', help='cover_request UUID')
    conf_p.add_argument('teacher_id', help='teachers.id UUID of the confirmed teacher')
    conf_p.add_argument('--dry-run', action='store_true')

    exp_p = sub.add_parser('expire', help='Mark past-class requests as expired')
    exp_p.add_argument('--dry-run', action='store_true')

    sub.add_parser('status', help='Print workflow status summary')

    args = ap.parse_args()

    if not args.cmd or args.cmd == 'run':
        run(dry_run=getattr(args, 'dry_run', False))
    elif args.cmd == 'confirm':
        confirm_cover(args.request_id, args.teacher_id,
                      dry_run=getattr(args, 'dry_run', False))
    elif args.cmd == 'expire':
        expire_stale_requests(dry_run=getattr(args, 'dry_run', False))
    elif args.cmd == 'status':
        print_status()
    else:
        ap.print_help()
