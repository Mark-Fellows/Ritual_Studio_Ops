"""
link_generator.py — Stage 7
=============================
Generates teacher portal URLs for cover candidates.

The portal URL encodes the cover_candidate_id (a UUID) as a token.
Because UUIDs are unguessable, no additional auth layer is needed for
this internal tool.

URL format:
    file:///path/to/teacher_portal.html?c=<cover_candidate_id>
    OR (when hosted):
    https://your-domain.com/teacher_portal.html?c=<cover_candidate_id>

Usage
-----
    # Generate links for all candidates on a request
    python stage7/link_generator.py --request-id <uuid>

    # Print link for a single candidate
    python stage7/link_generator.py --candidate-id <uuid>

    # Output personalised WhatsApp messages with links
    python stage7/link_generator.py --request-id <uuid> --format whatsapp

Environment
-----------
    PORTAL_BASE_URL — base URL of the portal HTML file
                      e.g. https://cover.ritualstudios.com.au/teacher_portal.html
                      Defaults to the local file:// path.
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import sb_get  # noqa: E402

# ─── Config ───────────────────────────────────────────────────────────────────

_THIS_DIR    = Path(__file__).parent
_PORTAL_FILE = _THIS_DIR / 'teacher_portal.html'
_LOCAL_URL   = _PORTAL_FILE.resolve().as_uri()
PORTAL_BASE  = os.getenv('PORTAL_BASE_URL', _LOCAL_URL).split('?')[0].rstrip('/')


# ─── Core ─────────────────────────────────────────────────────────────────────

def portal_url(cover_candidate_id: str) -> str:
    """Return the full portal URL for a given candidate ID."""
    return f'{PORTAL_BASE}?c={cover_candidate_id}'


def get_candidates_for_request(cover_request_id: str) -> list[dict]:
    """Fetch all cover_candidates for a request with teacher contact details."""
    return sb_get('cover_candidates', params={
        'cover_request_id': f'eq.{cover_request_id}',
        'select': (
            'cover_candidate_id,response,is_confirmed,contacted_at,match_score,'
            'teachers(id,first_name,last_name,email,whatsapp_phone)'
        ),
        'order': 'match_score.desc',
    })


def generate_links(cover_request_id: str) -> list[dict]:
    """
    Generate portal links for all candidates on a request.
    Returns a list of dicts with teacher info and portal URL.
    """
    results = []
    for c in get_candidates_for_request(cover_request_id):
        t = c.get('teachers') or {}
        results.append({
            'cover_candidate_id': c['cover_candidate_id'],
            'teacher_name':  f"{t.get('first_name','')} {t.get('last_name','')}".strip(),
            'email':         t.get('email') or '',
            'whatsapp_phone':t.get('whatsapp_phone') or '',
            'response':      c.get('response') or 'pending',
            'is_confirmed':  c.get('is_confirmed') or False,
            'match_score':   c.get('match_score') or 0,
            'portal_url':    portal_url(c['cover_candidate_id']),
        })
    return results


def format_whatsapp_message(request: dict, candidate: dict) -> str:
    """Build a personalised WhatsApp message including the candidate's portal link."""
    from stage4.notifier import fmt_date, fmt_time_range  # noqa: E402
    first  = (candidate['teacher_name'].split()[0] if candidate['teacher_name'] else 'there')
    cls    = (request.get('class_name_raw') or request.get('discipline_code') or 'class').title()
    date_s = fmt_date(request.get('class_date'))
    time_s = fmt_time_range(request.get('class_time'), request.get('class_end_time'))
    studio = request.get('studio') or 'TBC'
    for_   = request.get('requesting_teacher_name_raw') or 'another teacher'
    link   = candidate['portal_url']
    return (
        f'Hi {first} \U0001f64f\n\n'
        f'A cover is needed and you\u2019ve been matched!\n\n'
        f'Class:   {cls}\nDate:    {date_s}\nTime:    {time_s}\n'
        f'Studio:  {studio}\nFor:     {for_}\n\n'
        f'Please respond here:\n{link}\n\nThank you! \U0001f340'
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate teacher portal links for cover candidates'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--request-id',   metavar='UUID', help='Generate links for all candidates on this request')
    group.add_argument('--candidate-id', metavar='UUID', help='Generate link for a single candidate')
    parser.add_argument(
        '--format', choices=['table', 'whatsapp', 'urls'], default='table',
        help='Output format: table (default), whatsapp message text, or plain URLs'
    )
    args = parser.parse_args()

    if args.candidate_id:
        print(portal_url(args.candidate_id))
        sys.exit(0)

    requests = sb_get('cover_requests', params={
        'cover_request_id': f'eq.{args.request_id}', 'limit': '1'
    })
    if not requests:
        print(f'ERROR: cover_request {args.request_id} not found.')
        sys.exit(1)
    request = requests[0]

    links = generate_links(args.request_id)
    if not links:
        print('No candidates found for this request.')
        sys.exit(0)

    if args.format == 'urls':
        for l in links:
            print(f'{l["teacher_name"]:30s}  {l["portal_url"]}')

    elif args.format == 'whatsapp':
        for l in links:
            print(f'\n{"─"*60}')
            print(f'To: {l["teacher_name"]}  ({l["whatsapp_phone"] or l["email"] or "no contact"})')
            print('─'*60)
            try:
                print(format_whatsapp_message(request, l))
            except Exception as e:
                print(f'(message format error: {e})')
                print(l['portal_url'])

    else:
        print(f'\nPortal links for request {args.request_id}')
        print(f'Base: {PORTAL_BASE}\n')
        print(f'{"Teacher":<28} {"Score":>5}  {"Response":<14} URL')
        print('─' * 100)
        for l in links:
            confirmed = ' (confirmed)' if l['is_confirmed'] else ''
            print(f'{l["teacher_name"]:<28} {l["match_score"]:>5}  {l["response"]:<14}{confirmed}  {l["portal_url"]}')
