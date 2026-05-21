"""
generate_timetable_html.py

Reads data/momence_classes_future.csv and writes a self-contained
public/studio_timetable.html that renders both Robina and Palm Beach as a
continuous-time-axis calendar week. The page embeds every full week
present in the CSV plus a toolbar (week-ending picker, multi-select
discipline pills, teacher dropdown, settings cog) so the user can switch
view without re-running this script.

Teacher names are enriched from the Supabase momence_sessions table
(populated by sync_sessions_to_supabase.py in the Momence_data pipeline).
The CSV export always contains NA for Teacher; Supabase holds the actual
names fetched via the Momence per-session detail API.  If Supabase is
unavailable the timetable is still generated -- teacher fields are simply
left blank.

The HTML scaffold itself lives in tools/timetable_template.html with
__PAYLOAD_JSON__ as the placeholder.

Usage:
    python tools/generate_timetable_html.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# Allow importing config.py from the project root regardless of CWD.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Attempt to load the Supabase helper.  If config or its dependencies are
# missing (e.g. python-dotenv not installed) we fall back to no enrichment.
try:
    from config import sb_get as _sb_get
    _SUPABASE_AVAILABLE = True
except Exception as _e:
    print(f"[WARN] Could not import config.sb_get -- teacher lookup disabled: {_e}")
    _SUPABASE_AVAILABLE = False

CSV_PATH = PROJECT_ROOT / "data" / "momence_classes_future.csv"
TEMPLATE_PATH = PROJECT_ROOT / "tools" / "timetable_template.html"
JS_PATH = PROJECT_ROOT / "tools" / "timetable_logic.js"
OUT_PATH = PROJECT_ROOT / "public" / "studio_timetable.html"

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STUDIOS = ["Robina", "Palm Beach"]

DISCIPLINE_PATTERNS = (
    ("reformer",        "Reformer"),
    ("pilates mat",     "Pilates Mat"),
    ("mat pilates",     "Pilates Mat"),
    ("power pilates",   "Pilates Mat"),
    ("free pilates",    "Pilates Mat"),
    ("yin",             "Yin"),
    ("barre",           "Barre"),
    ("vinyasa",         "Yoga"),
    ("yoga",            "Yoga"),
)

DISCIPLINE_COLOURS = {
    # 2026-05-09 palette: Reformer purple, Barre deeper blue, Yin deeper
    # green, Pilates Mat light blue, Yoga light green.
    "Reformer":    ("#e9d5ff", "#6b21a8"),  # purple-200 / purple-800
    "Pilates Mat": ("#dbeafe", "#1e40af"),  # blue-100   / blue-800   (light blue)
    "Barre":       ("#93c5fd", "#1e3a8a"),  # blue-300   / blue-900   (deeper blue)
    "Yin":         ("#86efac", "#14532d"),  # green-300  / green-900  (deeper green)
    "Yoga":        ("#dcfce7", "#166534"),  # green-100  / green-800  (light green)
    "Other":       ("#e5e7eb", "#374151"),  # neutral
}


def fetch_teacher_lookup() -> dict[str, dict]:
    """Query momence_sessions and return {session_id_str: {teacher, substitute}}.

    Only fetches rows where teacher IS NOT NULL so the payload is small.
    Returns an empty dict and prints a warning if Supabase is unreachable.
    """
    if not _SUPABASE_AVAILABLE:
        return {}
    try:
        rows = _sb_get(
            "momence_sessions",
            params={
                "select": "session_id,teacher,substitute",
                "teacher": "not.is.null",
                "limit": "10000",
            },
        )
        lookup = {
            str(r["session_id"]): {
                "teacher":    r.get("teacher"),
                "substitute": r.get("substitute"),
            }
            for r in rows
            if r.get("session_id") is not None
        }
        print(f"Teacher lookup loaded: {len(lookup)} sessions with teacher data.")
        return lookup
    except Exception as exc:
        print(f"[WARN] Supabase teacher lookup failed -- continuing without: {exc}")
        return {}


def classify_studio(loc: str) -> str:
    if not loc:
        return ""
    if "Robina" in loc or "(RS)" in loc:
        return "Robina"
    if "Palm Beach" in loc or "(PB)" in loc:
        return "Palm Beach"
    return ""


def classify_discipline(class_name: str) -> str:
    n = (class_name or "").strip().lower()
    for needle, canonical in DISCIPLINE_PATTERNS:
        if needle in n:
            return canonical
    return "Other"


def parse_csv() -> list[dict]:
    out: list[dict] = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["Date"], "%d %b %Y").date()
            except (KeyError, ValueError):
                continue
            studio = classify_studio(r.get("Location") or "")
            if studio not in STUDIOS:
                continue
            try:
                start_str, end_str = [t.strip() for t in (r["Time"] or "").split("-")]
                start_t = datetime.strptime(start_str, "%H:%M").time()
                end_t = datetime.strptime(end_str, "%H:%M").time()
            except (KeyError, ValueError):
                continue
            class_name = (r.get("Class Name") or "").strip()
            location = (r.get("Location") or "").strip()
            cap = (r.get("Capacity") or "").strip()
            signups = (r.get("Signups") or "").strip()
            teacher = (r.get("Teacher") or "").strip()
            substitute = (r.get("Substitute") or "").strip()
            duration = (
                (end_t.hour * 60 + end_t.minute)
                - (start_t.hour * 60 + start_t.minute)
            ) or 50
            out.append({
                "id": (r.get("Class Number") or "").strip(),
                "name": class_name,
                "discipline": classify_discipline(class_name),
                "date": d.isoformat(),
                "weekday": WEEKDAYS[d.weekday()],
                "start": start_t.strftime("%H:%M"),
                "end": end_t.strftime("%H:%M"),
                "start_minutes": start_t.hour * 60 + start_t.minute,
                "duration_minutes": duration,
                "studio": studio,
                "location": location,
                "room": location.split("(")[-1].rstrip(")") if "(" in location else "",
                "capacity": cap if cap and cap != "NA" else None,
                "signups": signups if signups and signups != "NA" else None,
                "teacher": teacher if teacher and teacher != "NA" else None,
                "substitute": substitute if substitute and substitute != "NA" else None,
            })
    return out


def group_by_week(rows: list[dict]) -> dict[str, list[dict]]:
    by_week: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        d = date.fromisoformat(r["date"])
        week_start = d - timedelta(days=d.weekday())
        by_week[week_start.isoformat()].append(r)
    return dict(sorted(by_week.items()))


def render_html(payload: dict) -> str:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Timetable template not found at {TEMPLATE_PATH}. "
            "It must live alongside generate_timetable_html.py."
        )
    if not JS_PATH.exists():
        raise FileNotFoundError(
            f"Timetable JS not found at {JS_PATH}."
        )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    js_source = JS_PATH.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, separators=(",", ":"))
    for placeholder in ("__PAYLOAD_JSON__", "__TIMETABLE_JS__"):
        if placeholder not in template:
            raise RuntimeError(
                f"Template is missing the {placeholder} placeholder."
            )
    return (
        template
        .replace("__TIMETABLE_JS__", js_source)
        .replace("__PAYLOAD_JSON__", payload_json)
    )


def main() -> int:
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        return 1

    # Fetch teacher names from Supabase before parsing CSV.
    # The CSV always has NA for Teacher; Supabase holds the real names.
    teacher_lookup = fetch_teacher_lookup()

    rows = parse_csv()
    print(f"Parsed {len(rows)} class rows from CSV.")

    # Apply teacher lookup: fill in teacher/substitute where CSV has None.
    enriched = 0
    for row in rows:
        info = teacher_lookup.get(row["id"])
        if info:
            if not row["teacher"] and info.get("teacher"):
                row["teacher"] = info["teacher"]
                enriched += 1
            if not row["substitute"] and info.get("substitute"):
                row["substitute"] = info["substitute"]
    if teacher_lookup:
        print(f"Teacher names applied to {enriched} of {len(rows)} rows.")

    weeks_map = group_by_week(rows)
    weeks_payload = []
    distinct_disciplines: set[str] = set()
    distinct_teachers: set[str] = set()
    for week_start, classes in weeks_map.items():
        weeks_payload.append({
            "week_start": week_start,
            "total": len(classes),
            "classes": classes,
        })
        for c in classes:
            distinct_disciplines.add(c["discipline"])
            if c["teacher"]:
                distinct_teachers.add(c["teacher"])

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "weeks": weeks_payload,
        "distinct_disciplines": sorted(distinct_disciplines),
        "distinct_teachers": sorted(distinct_teachers),
        "colours": DISCIPLINE_COLOURS,
    }
    print(f"Built payload: {len(weeks_payload)} weeks, "
          f"{len(distinct_disciplines)} disciplines, "
          f"{len(distinct_teachers)} teachers.")

    html = render_html(payload)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
