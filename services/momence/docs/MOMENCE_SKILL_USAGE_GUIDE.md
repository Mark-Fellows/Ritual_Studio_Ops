# MOMENCE-DATA SKILL - COMPLETE USAGE GUIDE

**Created:** 2025-02-01
**Purpose:** Prevent confusion and enable direct data extraction without trial-and-error

---

## CRITICAL: THIS IS NOT A CALLABLE TOOL

**WRONG APPROACH:**
```
❌ momence-data:query_bookings(...)
❌ momence-data:execute_sql(...)
❌ Any direct tool invocation
```

**CORRECT APPROACH:**
```
✅ Use Python REPL via Desktop Commander process tools
✅ Import the momence_api_client.py module
✅ Call methods on the client object
```

---

## SKILL TYPE AND LOCATION

- **Type:** Python library skill (not tool-based)
- **Location:** `/mnt/skills/user/momence-data/SKILL.md`
- **Python Client:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_api_client.py`
- **Credentials:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\.env`

---

## CREDENTIALS (CONFIRMED WORKING)

The `.env` file exists and contains all required credentials:

```
MOMENCE_CLIENT_ID=api-32083-t5PW3f5B2k7plzue
MOMENCE_CLIENT_SECRET=miZi44HVizs0eLU5FTOvXRPeslg0fxzj
MOMENCE_USERNAME=markjfellows@hotmail.com
MOMENCE_PASSWORD=Momence2007
MOMENCE_HOST_ID=32083
```

**Status:** ✅ Verified working - authentication successful on 2025-02-01

---

## STANDARD WORKFLOW FOR DATA EXTRACTION

### Step 1: Start Python REPL

```python
Tool: Desktop Commander:start_process
Parameters:
  command: "python -i"
  timeout_ms: 10000
```

### Step 2: Import and Initialize Client

```python
Tool: Desktop Commander:interact_with_process
Input:
  import sys
  sys.path.insert(0, r'C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data')
  from momence_api_client import MomenceAPIClient
  from datetime import datetime
  import pandas as pd
```

### Step 3: Authenticate

```python
Tool: Desktop Commander:interact_with_process
Input:
  client = MomenceAPIClient()
  client.authenticate()
  print("Authentication successful")
```

**Expected Output:**
```
[AUTH] Authenticating as markjfellows@hotmail.com...
[AUTH] SUCCESS: Authentication successful!
[AUTH]   Token expires in 3600 seconds
True
Authentication successful
```

### Step 4: Query Data

```python
Tool: Desktop Commander:interact_with_process
Input:
  start_date = datetime(2025, 1, 1)
  end_date = datetime(2025, 12, 31)
  response = client.get_sessions(start_date=start_date, end_date=end_date, page=0, page_size=100)
  print(f"Total sessions: {response['pagination']['totalCount']}")
```

---

## AVAILABLE API METHODS

### Core Data Retrieval

| Method | Parameters | Returns | Notes |
|--------|------------|---------|-------|
| `get_members(page, page_size)` | page (int), page_size (int, max 100) | Member list | 29,589 total members |
| `get_sessions(start_date, end_date, page, page_size)` | datetime objects, pagination | Session/class list | 55,035 total in 2025 |
| `get_session_bookings(session_id, page, page_size)` | session_id (int), pagination | Bookings for specific session | Includes attendance status |
| `get_member_sessions(member_id, page, page_size)` | member_id (int), pagination | Member's booking history | Individual attendance |
| `get_memberships(page, page_size)` | pagination | Membership products | 165 products |
| `get_tags(page, page_size)` | pagination | Customer/session tags | 217 tags |

### Bulk Export Methods (Auto-Paginated)

| Method | Returns | Notes |
|--------|---------|-------|
| `get_all_members()` | All members | Handles pagination automatically |
| `get_all_memberships()` | All membership products | Handles pagination automatically |
| `get_all_tags()` | All tags | Handles pagination automatically |

---

## API RESPONSE STRUCTURE

All endpoints return this format:

```python
{
    "payload": [
        # Array of data objects
        {...},
        {...}
    ],
    "pagination": {
        "totalCount": 29589,
        "page": 0,
        "pageSize": 100
    }
}
```

---

## KEY DATA FIELDS

### Session Object
```python
{
    'id': int,
    'name': str,                    # e.g., "Vinyasa Flow", "Reformer Pilates"
    'startsAt': str (ISO datetime), # e.g., "2025-01-15T09:00:00Z"
    'endsAt': str (ISO datetime),
    'location': {
        'id': int,
        'name': str                 # "Palm Beach", "Mermaid", "Robina"
    },
    'teacher': {
        'id': int,
        'name': str
    },
    'capacity': int,                # Maximum spots
    'spotsLeft': int,               # Available spots
    'waitlistCount': int
}
```

### Booking Object
```python
{
    'id': int,
    'memberId': int,
    'sessionId': int,
    'checkedIn': bool,              # Actual attendance
    'status': str,                  # 'confirmed', 'cancelled', etc.
    'createdAt': str (ISO datetime),
    'membership': {
        'name': str,                # Membership type used
        'id': int
    }
}
```

### Member Object
```python
{
    'id': int,
    'email': str,
    'firstName': str,
    'lastName': str,
    'phone': str,
    'createdAt': str (ISO datetime),
    'lastActivityAt': str (ISO datetime),
    'tags': [],                     # Array of tag objects
    'memberships': []               # Array of active memberships
}
```

---

## PERFORMANCE CONSIDERATIONS

### Rate Limits
- **Momence API:** ~100 requests/minute
- **Token lifespan:** 3600 seconds (1 hour), auto-refreshes
- **Pagination:** Maximum page_size = 100

### Data Volume (as of 2025-02-01)
- **Total members:** 29,589
- **Total sessions (2025):** 55,035
- **Total membership products:** 165
- **Total tags:** 217

### Efficient Querying Strategy

**For Large Datasets:**
1. Use date ranges to limit results
2. Paginate strategically (page_size=100)
3. For 55,035 sessions: requires 551 API calls
4. Consider sampling for exploratory analysis

**Example - Monthly Analysis:**
```python
# More efficient than pulling all sessions at once
for month in range(1, 13):
    month_start = datetime(2025, month, 1)
    month_end = datetime(2025, month + 1, 1)
    sessions = client.get_sessions(
        start_date=month_start,
        end_date=month_end,
        page=0,
        page_size=100
    )
    # Process monthly data
```

---

## COMMON QUERIES AND PATTERNS

### 1. Get Recent Class Schedule
```python
from datetime import datetime, timedelta

now = datetime.now()
last_week = now - timedelta(days=7)

sessions = client.get_sessions(
    start_date=last_week,
    end_date=now,
    page=0,
    page_size=100
)

for session in sessions['payload']:
    print(f"{session['name']} at {session['location']['name']}")
```

### 2. Analyse Class Fill Rates
```python
session_id = 12345
bookings = client.get_session_bookings(session_id)
booking_count = bookings['pagination']['totalCount']

# Get session details
session_response = client.get_sessions(...)
session = [s for s in session_response['payload'] if s['id'] == session_id][0]

fill_rate = (booking_count / session['capacity']) * 100
print(f"Fill rate: {fill_rate:.1f}%")
```

### 3. Member Attendance History
```python
member_id = 54321
member_bookings = client.get_member_sessions(member_id)

attended_count = sum(1 for b in member_bookings['payload'] if b['checkedIn'])
total_bookings = member_bookings['pagination']['totalCount']

attendance_rate = (attended_count / total_bookings) * 100
print(f"Attendance rate: {attendance_rate:.1f}%")
```

### 4. Extract to Pandas DataFrame
```python
import pandas as pd

# Get all sessions
all_sessions = []
page = 0
while True:
    response = client.get_sessions(
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 12, 31),
        page=page,
        page_size=100
    )
    all_sessions.extend(response['payload'])
    
    if len(all_sessions) >= response['pagination']['totalCount']:
        break
    page += 1

# Convert to DataFrame
df = pd.DataFrame(all_sessions)
df['startsAt'] = pd.to_datetime(df['startsAt'])
df['location_name'] = df['location'].apply(lambda x: x['name'] if isinstance(x, dict) else 'Unknown')
```

---

## DISCIPLINE EXTRACTION LOGIC

Momence doesn't have a specific "discipline" field. Extract from session name:

```python
def extract_discipline(session_name):
    """Extract discipline from session name."""
    name_lower = str(session_name).lower()
    
    if 'reformer' in name_lower:
        return 'Reformer Pilates'
    elif 'mat pilates' in name_lower or 'mat' in name_lower:
        return 'Mat Pilates'
    elif 'barre' in name_lower:
        return 'Barre'
    elif 'yin' in name_lower:
        return 'Yin Yoga'
    elif 'yoga' in name_lower:
        return 'Yoga'
    else:
        return 'Other'
```

---

## RITUAL-SPECIFIC CONTEXT

### Locations
- **Palm Beach:** 2 studios/rooms
- **Mermaid:** 1 studio/room
- **Robina:** 2 studios/rooms
- **Total:** 5 studios across 3 locations

### Disciplines Offered
1. Yoga
2. Mat Pilates
3. Barre Pilates
4. Reformer Pilates
5. Yin Yoga

### Software Ecosystem
- **Momence:** Class scheduling, bookings, teacher management
- **Xero:** Accounting
- **Asana:** Task/project management
- **Slack:** Internal communications
- **WhatsApp:** Teacher community communications
- **Email/SMS:** Student communications

---

## TROUBLESHOOTING

### Problem: Authentication Fails

**Check:**
1. `.env` file exists at correct path
2. All 5 credentials are present
3. Credentials haven't changed
4. Internet connection active

**Solution:**
```python
# Verify .env is loaded
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(r'C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\.env')
load_dotenv(dotenv_path=env_path)

print(f"Client ID: {os.getenv('MOMENCE_CLIENT_ID')[:10]}...")  # First 10 chars
print(f"Host ID: {os.getenv('MOMENCE_HOST_ID')}")
```

### Problem: Module Not Found

**Error:** `ModuleNotFoundError: No module named 'momence_api_client'`

**Solution:**
```python
# Add path BEFORE importing
import sys
sys.path.insert(0, r'C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data')
```

### Problem: Token Expired

**Error:** Authentication fails after 1 hour

**Solution:** The client handles auto-refresh, but you can manually re-authenticate:
```python
client.authenticate()
```

### Problem: Rate Limit Hit

**Error:** Too many requests

**Solution:** Add delays between API calls:
```python
import time

for page in range(100):
    response = client.get_sessions(...)
    time.sleep(0.6)  # ~100 requests/minute = 1 per 0.6 seconds
```

---

## TESTED AND VERIFIED (2025-02-01)

✅ **Authentication:** Successful  
✅ **Session Retrieval:** 55,035 sessions found for 2025  
✅ **Credentials:** All present and valid  
✅ **Python Client:** Functioning correctly  
✅ **Auto-pagination:** Available via `get_all_*()` methods  

---

## QUICK START CHECKLIST

For every data extraction session:

1. ☐ Start Python REPL: `Desktop Commander:start_process` with `python -i`
2. ☐ Add path: `sys.path.insert(0, r'C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data')`
3. ☐ Import: `from momence_api_client import MomenceAPIClient`
4. ☐ Import utilities: `from datetime import datetime; import pandas as pd`
5. ☐ Initialize: `client = MomenceAPIClient()`
6. ☐ Authenticate: `client.authenticate()`
7. ☐ Verify: Check for "[AUTH] SUCCESS" message
8. ☐ Query: Use appropriate `client.get_*()` method
9. ☐ Process: Convert to DataFrame or analyse directly

---

## EXAMPLE: COMPLETE 2025 BOOKING ANALYSIS

See separate file: `analyse_2025_bookings.py` in the same directory.

This script demonstrates:
- Full authentication flow
- Paginated data retrieval
- DataFrame conversion
- Multi-dimensional analysis (location, discipline, time)
- Excel export with charts

---

## REFERENCES

- **Skill Documentation:** `/mnt/skills/user/momence-data/SKILL.md`
- **Python Client:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\momence_api_client.py`
- **API Reference:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\references\api_reference.md` (if exists)
- **Momence API Docs:** https://developers.momence.com/docs/ (official)

---

## FINAL NOTES

**DO NOT:**
- Attempt to call this as a tool (it's a Python library)
- Assume it works like other MCP tools
- Skip the authentication step
- Forget to add the module path

**ALWAYS:**
- Use Python REPL via Desktop Commander
- Import the client explicitly
- Authenticate before querying
- Handle pagination for large datasets
- Consider rate limits for bulk operations

---

**Last Updated:** 2025-02-01  
**Last Tested:** 2025-02-01  
**Status:** Fully Operational
