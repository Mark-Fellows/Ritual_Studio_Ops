"""
process_momence_tag_queue.py - apply queued CleanSweep Momence tags (27 Oct 2026)

The cleansweep-admin server function queues a request in public.momence_tag_requests when someone
is made a CleanSweep cleaner with "Tag as Karma Yogi in Momence" ticked. This script, run on this
PC (nightly and optionally every 30 minutes), applies them with the Momence API:
  POST   /api/v2/host/members/{memberId}/tags/{tagId}   (add)
  DELETE /api/v2/host/members/{memberId}/tags/{tagId}   (remove; not used by the app today)

For each pending request it:
  1. finds the tag by name (e.g. "Karma Yogi"); if the tag does not exist yet the request stays
     pending with a note, so it succeeds once the tag is created in Momence;
  2. finds the Momence customer: the stored member ID, else the Supabase copy, else a Momence search
     by email; creates the customer only when the request was entered by hand (create_if_missing);
  3. assigns the tag, then marks the request done or failed and, on success, stamps
     user_profiles.cleansweep_karma_tagged_at and the Supabase copy's tags.

Run:   python process_momence_tag_queue.py            apply pending requests
       python process_momence_tag_queue.py --dry-run  show what would happen, change nothing
Exits quickly (no Momence sign-in) when the queue is empty.
"""
import re
import sys

from cs_common import Momence, batch_log, log, now_iso, require_config, sb

MAX_ATTEMPTS = 10


def mirror_member_id(email: str):
    rows = sb("GET", "momence_members", params={"select": "member_id,email", "email": f"ilike.{email}", "limit": "5"}) or []
    for r in rows:
        if str(r.get("email") or "").strip().lower() == email:
            return r["member_id"]
    return None


def resolve_member(mom: Momence, q: dict, dry: bool):
    """Returns (member_id or None, note)."""
    if q.get("momence_member_id"):
        return int(q["momence_member_id"]), "member ID from the request"
    email = str(q["email"]).strip().lower()
    mid = mirror_member_id(email)
    if mid:
        return mid, "found in the Supabase copy"
    mid = mom.find_member_id_by_email(email)
    if mid:
        return mid, "found by Momence search"
    if not q.get("create_if_missing"):
        return None, "No Momence customer has this email."
    if not (q.get("first_name") and q.get("last_name")):
        return None, "No Momence customer has this email, and a first and last name are needed to create one."
    if dry:
        return None, "would create a Momence customer"
    r = mom.request("POST", "/host/members",
                    body={"email": email, "firstName": q["first_name"], "lastName": q["last_name"]})
    if not r.ok:
        return None, f"Could not create the Momence customer: HTTP {r.status_code} {r.text[:200]}"
    try:
        created = r.json() or {}
    except ValueError:
        created = {}
    mid = created.get("id") if isinstance(created.get("id"), int) else mom.find_member_id_by_email(email)
    return (mid, "created in Momence") if mid else (None, "Created the Momence customer, but could not read its ID yet.")


def apply_one(mom: Momence, q: dict, tags_by_name: dict, dry: bool):
    """Returns (status, member_id, note). status is done | failed | pending (retry) | dry."""
    tag = tags_by_name.get(str(q["tag_name"]).strip().lower())
    if not tag:
        return "pending", q.get("momence_member_id"), (
            f"The tag '{q['tag_name']}' does not exist in Momence. Create it in Momence; this request will then be applied.")
    mid, how = resolve_member(mom, q, dry)
    if not mid:
        retry = how.startswith("Created the Momence customer")
        return ("pending" if retry else ("dry" if dry else "failed")), None, how
    if dry:
        return "dry", mid, f"would {q['action']} tag {tag.get('id')} on member {mid} ({how})"
    path = f"/host/members/{mid}/tags/{tag['id']}"
    r = mom.request("POST" if q["action"] == "add" else "DELETE", path)
    if r.ok:
        return "done", mid, f"Tag {'added' if q['action'] == 'add' else 'removed'} ({how})"
    text = (r.text or "")[:200]
    if q["action"] == "add" and r.status_code in (400, 409, 422) and re.search(r"already|exist|assigned", text, re.I):
        return "done", mid, "Already tagged in Momence"
    if r.status_code in (400, 403, 404):
        return "failed", mid, f"Momence refused the change: HTTP {r.status_code} {text}"
    return "pending", mid, f"Momence error HTTP {r.status_code} {text}; will retry"


def after_success(q: dict, mid: int, tag: dict):
    if q["action"] != "add":
        return
    stamp = now_iso()
    if q.get("user_profile_id"):
        sb("PATCH", "user_profiles", params={"id": f"eq.{q['user_profile_id']}"}, prefer="return=minimal",
           body={"cleansweep_karma_tagged_at": stamp})
        sb("PATCH", "user_profiles", params={"id": f"eq.{q['user_profile_id']}", "momence_member_id": "is.null"},
           prefer="return=minimal", body={"momence_member_id": mid})
    rows = sb("GET", "momence_members", params={"select": "member_id,tags", "member_id": f"eq.{mid}"}) or []
    if rows:
        tags = rows[0].get("tags") or []
        if not any(str((t or {}).get("name", "")).strip().lower() == str(tag.get("name", "")).strip().lower() for t in tags):
            tags = tags + [{"id": tag.get("id"), "name": tag.get("name")}]
            sb("PATCH", "momence_members", params={"member_id": f"eq.{mid}"}, prefer="return=minimal",
               body={"tags": tags})


def main(argv) -> int:
    dry = "--dry-run" in argv
    require_config()
    queue = sb("GET", "momence_tag_requests",
               params={"select": "*", "status": "eq.pending", "order": "requested_at.asc", "limit": "50"}) or []
    if not queue:
        log("No pending CleanSweep tag requests.")
        return 0
    log(f"{len(queue)} pending tag request(s).")
    try:
        mom = Momence()
        tags_by_name = {str(t.get("name") or "").strip().lower(): t for t in mom.get_all_tags()}
    except Exception as e:
        log(f"FAILED to reach Momence: {e}")
        if not dry:
            batch_log(f"ERROR: CleanSweep tag queue could not reach Momence: {str(e)[:200]}")
        return 1

    counts = {"done": 0, "failed": 0, "pending": 0, "dry": 0}
    for q in queue:
        try:
            status, mid, note = apply_one(mom, q, tags_by_name, dry)
        except Exception as e:
            status, mid, note = "pending", q.get("momence_member_id"), f"Error: {str(e)[:200]}; will retry"
        attempts = int(q.get("attempts") or 0) + 1
        if status == "pending" and attempts >= MAX_ATTEMPTS:
            status, note = "failed", f"{note} (gave up after {attempts} attempts)"
        counts[status] = counts.get(status, 0) + 1
        log(f"  {q['email']}: {status} - {note}")
        if dry:
            continue
        patch = {"status": status, "attempts": attempts, "result_note": note[:500]}
        if mid:
            patch["momence_member_id"] = mid
        if status in ("done", "failed"):
            patch["processed_at"] = now_iso()
        sb("PATCH", "momence_tag_requests", params={"id": f"eq.{q['id']}"}, prefer="return=minimal", body=patch)
        if status == "done":
            try:
                after_success(q, mid, tags_by_name.get(str(q["tag_name"]).strip().lower()) or {"name": q["tag_name"]})
            except Exception as e:
                log(f"    tag applied, but the Supabase follow-up failed: {e}")

    summary = ", ".join(f"{k} {v}" for k, v in counts.items() if v)
    log(f"Finished: {summary}.")
    if not dry:
        batch_log(f"CleanSweep tag queue: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
