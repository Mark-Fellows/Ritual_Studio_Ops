"""
dashboard_sessions.py — Load sessions from Ritual Dashboard extracted data
==========================================================================

Instead of querying the Momence API (which returns old test data),
this module loads class data from the Ritual Dashboard's extracted
momence_YYYYMMDD.json files in the data/raw directory.

Usage:
    from dashboard_sessions import load_sessions_for_date
    sessions = load_sessions_for_date(target_date=date(2026, 6, 2))
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# Path to Ritual Dashboard data directory
DASHBOARD_DATA_DIR = Path(
    r"C:\Users\markj\OneDrive\Desktop\Ritual Dashboard\dashboard\data\raw"
)


def find_latest_momence_file() -> Optional[Path]:
    """Find the most recent momence_YYYYMMDD.json file."""
    if not DASHBOARD_DATA_DIR.exists():
        raise FileNotFoundError(f"Dashboard data dir not found: {DASHBOARD_DATA_DIR}")

    momence_files = sorted(DASHBOARD_DATA_DIR.glob("momence_*.json"), reverse=True)
    return momence_files[0] if momence_files else None


def load_dashboard_data() -> dict:
    """Load the latest Momence data from Ritual Dashboard."""
    file_path = find_latest_momence_file()
    if not file_path:
        raise FileNotFoundError(
            f"No momence_*.json files found in {DASHBOARD_DATA_DIR}"
        )

    print(f"  [DASHBOARD] Loading {file_path.name}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def load_sessions_for_date(target_date: date, lookback_days: int = 1) -> list[dict]:
    """
    Load sessions from dashboard data for target_date ± lookback_days.

    Args:
        target_date: Date to fetch sessions for
        lookback_days: Include sessions from +/- this many days

    Returns:
        List of session dicts from dashboard (transformed to match Momence format)
    """
    data = load_dashboard_data()
    classes = data.get("classes", [])

    # Calculate date range
    start = target_date - timedelta(days=lookback_days)
    end = target_date + timedelta(days=lookback_days)

    print(f"  [DASHBOARD] Querying {len(classes)} classes for {start} to {end}")

    # Filter classes in date range
    matching = []
    for cls in classes:
        try:
            cls_date = date.fromisoformat(cls.get("date", ""))
            if start <= cls_date <= end:
                # Transform dashboard class to session-like dict
                session = transform_class_to_session(cls)
                matching.append(session)
        except (ValueError, TypeError):
            continue

    print(f"  [DASHBOARD] Found {len(matching)} classes in range")
    return matching


def transform_class_to_session(cls: dict) -> dict:
    """
    Transform a dashboard class object to a session dict compatible
    with the Momence API response format.
    """
    # Parse time and date
    try:
        time_parts = cls.get("time", "").split(":") if cls.get("time") else []
        hour = int(time_parts[0]) if len(time_parts) > 0 else 0
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        cls_date = cls.get("date", "")
        if cls_date:
            dt = datetime.fromisoformat(f"{cls_date}T{hour:02d}:{minute:02d}:00")
        else:
            dt = None
    except (ValueError, TypeError):
        dt = None

    # Parse instructor name
    instructor_raw = cls.get("instructor", "") or ""
    instructor_parts = instructor_raw.split() if instructor_raw else []
    instructor = (
        {
            "firstName": instructor_parts[0] if len(instructor_parts) > 0 else "",
            "lastName": (
                " ".join(instructor_parts[1:]) if len(instructor_parts) > 1 else ""
            ),
        }
        if instructor_raw
        else {}
    )

    # Parse studio/location
    studio_name = cls.get("studio", "") or ""
    location = {"name": studio_name}

    # Map class type to discipline code
    class_type = cls.get("class_type", cls.get("class_name", "")).lower()
    discipline = infer_discipline_from_class_name(class_type)

    # Build session dict in Momence format
    session = {
        "id": cls.get("class_id"),
        "name": cls.get("class_name", ""),
        "title": cls.get("class_name", ""),
        "type": "fitness",
        "startsAt": dt.isoformat() + "Z" if dt else None,
        "startTime": cls.get("time", ""),
        "durationInMinutes": 60,  # Default
        "capacity": cls.get("capacity"),
        "bookingCount": cls.get("bookings_count", 0),
        "teacher": instructor if instructor else None,
        "inPersonLocation": location,
        "location": location,
        "isInPerson": True,
        "isDraft": False,
        # Dashboard-specific additions
        "_source": "dashboard",
        "_dashboard_class": cls,
    }

    return session


def infer_discipline_from_class_name(name: str) -> str:
    """Map class name to discipline code."""
    name_lower = name.lower()

    if "reformer" in name_lower:
        return "reformer"
    elif "mat" in name_lower and "pilates" in name_lower:
        return "mat_pilates"
    elif "barre" in name_lower:
        return "barre"
    elif "yin" in name_lower:
        return "yin"
    elif "yoga" in name_lower:
        return "yoga"

    return None
