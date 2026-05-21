# Momence API v2 - Complete Endpoint Reference

**Generated:** 2026-01-30  
**Base URL:** `https://api.momence.com/api/v2`  
**Authentication:** OAuth 2.0 Password Flow

---

## Summary of Available Endpoints

| # | Endpoint | Description | Records | Status |
|---|----------|-------------|---------|--------|
| 1 | `/host/members` | Customer database | 29,589 | ✅ Works |
| 2 | `/host/sessions` | Class schedule | 55,012 | ✅ Works |
| 3 | `/host/sessions/{id}/bookings` | Bookings per session | Varies | ✅ Works |
| 4 | `/host/memberships` | Membership types/products | 165 | ✅ Works |
| 5 | `/host/members/{id}/sessions` | Bookings by member | Varies | ✅ Works |
| 6 | `/host/tags` | Available tags | 217 | ✅ Works |
| 7 | `/host/sales` | Sales/transactions | ? | ❌ Forbidden |
| 8 | `/host/teachers` | Teachers/instructors | N/A | ❌ Not Available |

---

## Endpoint 1: Members

**URL:** `GET /host/members`

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 100 |
| `search` | str | No | Search name/email |
| `email` | str | No | Filter exact email |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique member ID |
| `firstName` | str | First name |
| `lastName` | str | Last name |
| `email` | str | Email address |
| `phoneNumber` | str | Phone number |
| `pictureUrl` | str | Profile picture URL |
| `firstSeen` | str | First visit (ISO 8601) |
| `lastSeen` | str | Last visit (ISO 8601) |
| `visits` | dict | Visit statistics |
| `customerTags` | list | Assigned tags |
| `customerFields` | list | Custom field values |

---

## Endpoint 2: Sessions

**URL:** `GET /host/sessions`

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 200 |
| `startDate` | str | No | From date (YYYY-MM-DD) |
| `endDate` | str | No | To date (YYYY-MM-DD) |
| `type` | str | No | Session type filter |
| `isCancelled` | str | No | Cancellation filter |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique session ID |
| `name` | str | Session/class name |
| `type` | str | Session type |
| `description` | str | Description |
| `startsAt` | str | Start datetime (ISO 8601) |
| `endsAt` | str | End datetime (ISO 8601) |
| `durationInMinutes` | int | Duration |
| `capacity` | int | Maximum capacity |
| `bookingCount` | int | Current bookings |
| `isInPerson` | bool | In-person flag |
| `isCancelled` | bool | Cancelled status |
| `isDraft` | bool | Draft status |
| `isRecurring` | bool | Recurring flag |
| `teacher` | dict | **Always null** ⚠️ |
| `tags` | list | Session tags |
| `inPersonLocation` | dict | Location details |
| `onlineStreamUrl` | str | Virtual meeting URL |
| `bannerImageUrl` | str | Banner image |

---

## Endpoint 3: Session Bookings

**URL:** `GET /host/sessions/{sessionId}/bookings`

### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sessionId` | int | Yes | Session ID from Endpoint 2 |

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 100 |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Booking ID |
| `createdAt` | str | Booking datetime (ISO 8601) |
| `cancelledAt` | str | Cancellation datetime |
| `checkedIn` | bool | Check-in status |
| `isRecurring` | bool | Recurring booking flag |
| `recurringBookingId` | int | Parent recurring ID |
| `ticketsBought` | int | Number of tickets |
| `roomSpotId` | int | Reserved spot |
| `member` | dict | **Nested member object** |

### Nested: member
| Field | Type |
|-------|------|
| `id` | int |
| `firstName` | str |
| `lastName` | str |
| `email` | str |
| `phoneNumber` | str |
| `pictureUrl` | str |

---

## Endpoint 4: Memberships (Product Types)

**URL:** `GET /host/memberships`

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 100 |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Membership type ID |
| `name` | str | Membership name |
| `description` | str | Description text |
| `type` | str | Type (e.g., "subscription") |
| `price` | int | Price (cents or dollars) |
| `priceType` | str | Pricing model |
| `priceIncludesTax` | bool | Tax included |
| `taxRateInPercent` | int | Tax rate |
| `duration` | int | Duration value |
| `durationUnit` | str | Duration unit (days/months) |
| `autoRenewing` | bool | Auto-renew enabled |
| `minimumAutoRenews` | int | Minimum renewal cycles |
| `hasFreeTrial` | bool | Free trial available |
| `freeTrialDurationInDays` | int | Trial length |
| `freeTrialPrice` | int | Trial price |
| `isIntroOffer` | bool | Intro offer flag |
| `isActivatedOnFirstUse` | bool | Activation timing |
| `disabled` | bool | Disabled status |
| `featured` | bool | Featured flag |
| `order` | int | Display order |
| `startDate` | str | Availability start |
| `endDate` | str | Availability end |
| `eventCredits` | int | Event credit amount |
| `moneyCredits` | int | Money credit amount |
| `usageLimitForSessions` | int | Session usage limit |
| `usageLimitForAppointments` | int | Appointment limit |
| `contractAgreement` | str | Contract text |
| `tags` | list | Associated tags |
| `locationId` | int | Location restriction |

---

## Endpoint 5: Member Session Bookings (by Member)

**URL:** `GET /host/members/{memberId}/sessions`

### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memberId` | int | Yes | Member ID from Endpoint 1 |

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 100 |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Booking ID |
| `createdAt` | str | Booking datetime |
| `cancelledAt` | str | Cancellation datetime |
| `checkedIn` | bool | Check-in status |
| `roomSpotId` | int | Reserved spot |
| `session` | dict | **Nested session object** |

### Nested: session
| Field | Type |
|-------|------|
| `id` | int |
| `name` | str |
| `type` | str |
| `startsAt` | str |
| `endsAt` | str |
| `durationInMinutes` | int |
| `capacity` | int |
| `description` | str |
| `isInPerson` | bool |
| `isRecurring` | bool |
| `teacher` | dict (null) |

---

## Endpoint 6: Tags

**URL:** `GET /host/tags`

### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | Yes | Page number (0-indexed) |
| `pageSize` | int | Yes | Max 100 |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Tag ID |
| `name` | str | Tag name |
| `isCustomerBadge` | bool | Display as badge |
| `badgeLabel` | str | Badge display text |
| `badgeColor` | str | Badge color |

---

## Response Structure

All endpoints return:
```json
{
  "payload": [ ... ],
  "pagination": {
    "page": 0,
    "pageSize": 100,
    "totalCount": 29589
  }
}
```

---

## Entity Relationships

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────┐
│   MEMBERS   │       │  SESSIONS   │       │    BOOKINGS     │
├─────────────┤       ├─────────────┤       ├─────────────────┤
│ id (PK)     │◄──┐   │ id (PK)     │◄──────│ session.id (FK) │
│ firstName   │   │   │ name        │       │ member.id (FK)──┼──┐
│ lastName    │   │   │ startsAt    │       │ id (PK)         │  │
│ email       │   │   │ type        │       │ checkedIn       │  │
│ customerTags│   │   │ capacity    │       │ createdAt       │  │
└─────────────┘   │   └─────────────┘       └─────────────────┘  │
                  │                                              │
                  └──────────────────────────────────────────────┘

┌─────────────┐       ┌─────────────┐
│ MEMBERSHIPS │       │    TAGS     │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ name        │       │ name        │
│ price       │       │ badgeLabel  │
│ type        │       │ badgeColor  │
│ duration    │       └─────────────┘
└─────────────┘
```

---

## Known Limitations

| Issue | Details |
|-------|---------|
| **No Teacher Data** | `teacher` field always returns `null` |
| **No Sales Access** | `/host/sales` returns 403 Forbidden |
| **No Staff Endpoint** | No way to retrieve instructor list |
| **Pagination Required** | `page` and `pageSize` always mandatory |

---

## Example: Full Data Export

```python
from momence_api_client import MomenceAPIClient
from datetime import datetime, timedelta, timezone

client = MomenceAPIClient()
client.authenticate()

# Get all members (paginated)
all_members = []
page = 0
while True:
    result = client.get_members(page=page, page_size=100)
    all_members.extend(result['payload'])
    if len(result['payload']) < 100:
        break
    page += 1

# Get sessions for date range
sessions = client.get_sessions(
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 1, 31),
    page=0, page_size=200
)

# Get bookings for each session
for session in sessions['payload']:
    bookings = client.get_session_bookings(
        session_id=session['id'],
        page=0, page_size=100
    )
```
