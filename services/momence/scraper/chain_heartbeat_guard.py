"""
chain_heartbeat_guard.py
========================

End-of-chain heartbeat guardrail for the Momence pipeline.

What it does
------------
Scans Log_files\\Momence_batch_log.txt and raises a visible alert when
*either* of the following is true:

  1. No 'Run_Momence_Chain.bat completed' line has appeared in the last
     <stale_after_hours> hours (default 26h — gives the 02:00 chain a
     2-hour grace window after its expected ~03:30 completion).

  2. The last line in the file does not end with a newline — i.e. the
     log was truncated mid-write by an interrupted append, which is what
     happened on 2026-05-17 00:21:05 and silently blocked every later
     write from any writer.

Alerts go to three channels (each is best-effort; any failure is logged
to stderr but does not stop the others):

  * stderr           – always
  * a desktop toast  – via PowerShell BurntToast (if installed) or
                       msg.exe (Windows fallback)
  * the master log   – appended as 'GUARD ALERT: ...' so the next
                       diagnostic run sees it inline

Exit codes
----------
  0  – healthy
  2  – stale chain (no completed line within window)
  3  – truncated tail detected
  4  – both stale and truncated
  5  – batch log not found

Usage
-----
  python chain_heartbeat_guard.py                     # default 26h window
  python chain_heartbeat_guard.py --hours 30          # custom window
  python chain_heartbeat_guard.py --quiet             # no toast

Schedule it as a Windows Task to run hourly between 04:00 and 23:00
local time. A single failed run does not retry; it relies on the next
hourly tick.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Master batch log location. Matches the resolution logic in config.py and
# every individual writer: prefer the local-only folder added 2026-05-18,
# fall back to the legacy in-tree path if that folder is missing.
_LOCAL_BATCH_LOG_DIR = r"C:\Users\markj\Momence_local_logs"
if os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG = os.path.join(_LOCAL_BATCH_LOG_DIR, "Momence_batch_log.txt")
else:
    BATCH_LOG = os.path.join(SCRIPT_DIR, "Log_files", "Momence_batch_log.txt")

# Pattern for a successful chain completion line written by Run_Momence_Chain.bat
COMPLETION_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-\s+Run_Momence_Chain\.bat completed"
)


def _now() -> _dt.datetime:
    return _dt.datetime.now()


def _read_tail_bytes(path: str, max_bytes: int = 500_000) -> bytes:
    """Read up to the last max_bytes of a file (whole file if smaller)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > max_bytes:
            f.seek(-max_bytes, os.SEEK_END)
        return f.read()


def find_last_completion(path: str) -> _dt.datetime | None:
    """Return the timestamp of the most recent 'Run_Momence_Chain.bat completed' line."""
    raw = _read_tail_bytes(path)
    text = raw.decode("utf-8", errors="replace")
    latest = None
    for line in text.splitlines():
        m = COMPLETION_RE.match(line.strip())
        if m:
            try:
                ts = _dt.datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if latest is None or ts > latest:
                latest = ts
    return latest


def is_tail_truncated(path: str) -> bool:
    """Return True if the file does not end with a newline (corrupt tail)."""
    if os.path.getsize(path) == 0:
        return False
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        return f.read(1) not in (b"\n",)


# ── alert channels ─────────────────────────────────────────────────────────

def _alert_stderr(msg: str) -> None:
    print(f"[GUARD ALERT] {msg}", file=sys.stderr)


def _alert_master_log(msg: str) -> None:
    """Best-effort append to the master log so the next diagnostic pick it up."""
    try:
        ts = _now().strftime("%Y-%m-%d %H:%M:%S")
        with open(BATCH_LOG, "a", encoding="utf-8") as f:
            f.write(f"{ts} - GUARD ALERT: {msg}\r\n")
    except Exception as e:
        print(f"[GUARD] could not write alert to master log: {e}", file=sys.stderr)


def _alert_toast(title: str, msg: str) -> None:
    """Best-effort Windows toast via BurntToast (PowerShell) with msg.exe fallback."""
    try:
        ps = (
            "if (Get-Module -ListAvailable -Name BurntToast) "
            "{ Import-Module BurntToast; "
            f"New-BurntToastNotification -Text '{title}', '{msg}' }} "
            "else { exit 1 }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=True,
            timeout=20,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    except Exception:
        pass
    try:
        subprocess.run(
            ["msg", "*", f"{title}: {msg}"],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def alert(msg: str, *, quiet: bool = False) -> None:
    _alert_stderr(msg)
    _alert_master_log(msg)
    if not quiet:
        _alert_toast("Momence chain heartbeat", msg)


# ── main ───────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hours",
        type=float,
        default=26.0,
        help="Stale threshold in hours since last chain completion (default 26).",
    )
    ap.add_argument("--quiet", action="store_true", help="Suppress desktop toast.")
    args = ap.parse_args(argv)

    if not os.path.exists(BATCH_LOG):
        alert(f"Master log missing: {BATCH_LOG}", quiet=args.quiet)
        return 5

    stale = False
    truncated = False

    last_complete = find_last_completion(BATCH_LOG)
    if last_complete is None:
        alert(
            "No 'Run_Momence_Chain.bat completed' line anywhere in the master log.",
            quiet=args.quiet,
        )
        stale = True
    else:
        age = _now() - last_complete
        if age > _dt.timedelta(hours=args.hours):
            hrs = age.total_seconds() / 3600
            alert(
                f"Last chain completion was {hrs:.1f}h ago "
                f"({last_complete.strftime('%Y-%m-%d %H:%M:%S')}); "
                f"threshold {args.hours:.1f}h.",
                quiet=args.quiet,
            )
            stale = True

    if is_tail_truncated(BATCH_LOG):
        alert(
            "Master log ends mid-line (no trailing newline) — "
            "subsequent appends are silently failing. "
            "Run the recovery: append CRLF to the file end.",
            quiet=args.quiet,
        )
        truncated = True

    if not stale and not truncated:
        print(
            f"[GUARD OK] last chain completion {last_complete.strftime('%Y-%m-%d %H:%M:%S')} "
            f"({(_now() - last_complete).total_seconds() / 3600:.1f}h ago); "
            "tail terminator present."
        )
        return 0

    rc = 0
    if stale:
        rc += 2
    if truncated:
        rc += 3
    if rc > 4:
        rc = 4  # cap at 4 = both
    return rc


if __name__ == "__main__":
    sys.exit(main())
