"""
sync_members.py - copy Momence customers into Supabase public.momence_members (27 Oct 2026)

Purpose: the CleanSweep person search (portal, Teacher Portal, CleanSweep Settings) finds Momence
customers in this table instead of calling Momence live, so the Momence login stays on this PC
(decision D1 = B).

Copies only: member ID, first name, last name, email and tags. Phone numbers are not copied.
Reading the table in the browser is limited to portal administrators (RLS); the CleanSweep search
reads it through the server function.

Run:   python sync_members.py              full copy (about 300 Momence API calls, ~4 minutes)
       python sync_members.py --dry-run    fetch the first page only, write nothing
       python sync_members.py --max-pages 3
Records each run in public.momence_sync_runs (entity = 'members'). Exit code 0 on success.
"""
import sys

from cs_common import Momence, batch_log, log, now_iso, require_config, sb

PAGE_SIZE = 100
UPSERT_BATCH = 500


def _arg(argv, name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else default
    return default


def clean_tags(raw):
    if not isinstance(raw, list):
        return None
    out = []
    for t in raw:
        if isinstance(t, dict) and (t.get("name") or t.get("id") is not None):
            out.append({"id": t.get("id"), "name": t.get("name")})
        elif isinstance(t, str):
            out.append({"id": None, "name": t})
    return out


def main(argv) -> int:
    dry = "--dry-run" in argv
    max_pages = int(_arg(argv, "--max-pages", "1" if dry else "0") or 0)
    require_config()

    run_id = None
    if not dry:
        rows = sb("POST", "momence_sync_runs", prefer="return=representation",
                  body={"entity": "members", "run_status": "running", "run_notes": "sync_members.py (CleanSweep)"})
        run_id = rows[0]["run_id"] if rows else None

    checked = upserted = errored = 0
    try:
        mom = Momence()
        page, total, batch = 0, None, []
        include_tags = None  # decided from the first page: never overwrite tags with NULL if the list omits them
        stamp = now_iso()

        def flush():
            nonlocal batch, upserted
            if not batch:
                return
            if not dry:
                sb("POST", "momence_members", params={"on_conflict": "member_id"},
                   prefer="resolution=merge-duplicates,return=minimal", body=batch)
            upserted += len(batch)
            batch = []

        while True:
            r = mom.request("GET", "/host/members", params={"page": page, "pageSize": PAGE_SIZE})
            if not r.ok:
                raise RuntimeError(f"Momence GET /host/members page {page}: HTTP {r.status_code} {r.text[:200]}")
            d = r.json() or {}
            rows = d.get("payload") or []
            total = (d.get("pagination") or {}).get("totalCount", total)
            if include_tags is None and rows:
                include_tags = any("tags" in x for x in rows)
                log(f"Momence member list {'includes' if include_tags else 'does not include'} tags.")
            for x in rows:
                mid = x.get("id")
                if not isinstance(mid, int):
                    errored += 1
                    continue
                row = {
                    "member_id": mid,
                    "first_name": (x.get("firstName") or "").strip() or None,
                    "last_name": (x.get("lastName") or "").strip() or None,
                    "email": (x.get("email") or "").strip() or None,
                    "updated_at": stamp,
                    "_synced_at": stamp,
                }
                if include_tags:
                    row["tags"] = clean_tags(x.get("tags")) or []
                batch.append(row)
                checked += 1
            if len(batch) >= UPSERT_BATCH:
                flush()
            page += 1
            if page % 25 == 0:
                log(f"  page {page}: {checked} customers read")
            if (not rows or len(rows) < PAGE_SIZE or (total is not None and checked + errored >= total)
                    or (max_pages and page >= max_pages)):
                break
        flush()

        status = "completed" if errored == 0 else "partial"
        log(f"Done: {checked} read, {upserted} {'would be ' if dry else ''}written, {errored} skipped (Momence total {total}).")
        if run_id:
            sb("PATCH", "momence_sync_runs", params={"run_id": f"eq.{run_id}"}, prefer="return=minimal",
               body={"completed_at": now_iso(), "rows_checked": checked, "rows_upserted": upserted,
                     "rows_errored": errored, "run_status": status})
        if not dry:
            batch_log(f"CleanSweep sync_members: {status}, {upserted} customers copied")
        return 0
    except Exception as e:
        log(f"FAILED: {e}")
        if run_id:
            try:
                sb("PATCH", "momence_sync_runs", params={"run_id": f"eq.{run_id}"}, prefer="return=minimal",
                   body={"completed_at": now_iso(), "rows_checked": checked, "rows_upserted": upserted,
                         "rows_errored": errored, "run_status": "failed", "error_message": str(e)[:500]})
            except Exception as e2:
                log(f"Could not record the failure: {e2}")
        if not dry:
            batch_log(f"ERROR: CleanSweep sync_members failed: {str(e)[:200]}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
