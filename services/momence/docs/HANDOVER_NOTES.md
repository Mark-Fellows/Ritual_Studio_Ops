# Handover Notes
**Date:** 30 March 2026
**Purpose:** Continuation context for a new chat session.

---

## 1. Leads Dashboard — completed

A new `leads.html` dashboard page was built and added to the Ritual Dashboard.

**File:** `Ritual Dashboard/dashboard/leads.html`

**Data source:** `momence_leads_2026_03_26_20_36.csv` (latest snapshot from `momence_leads_scrape.py`).
See `LEADS_SCRAPER.md` for full documentation of the leads scraper and its output schema.

**Dashboard contents:**
- 8 KPI cards: Total Leads (2,927), Converted to Customer (2,030), Active Pipeline (897), Conversion Rate (69.4%), New Leads — 7 Days (37), New Leads — 30 Days (94), Cold (1,143), Contacted (1,784).
- The 7-day and 30-day cards also show the percentage of those new leads that have been contacted: 45.9% (17/37) and 52.1% (49/94) respectively.
- Monthly trend chart — 12 months, bar + line overlay (new leads vs conversions).
- Lead health donut — Cold vs Contacted.
- Source breakdown — top 12 sources, total vs converted bars with conversion rate tooltip.
- Conversion rate by source — horizontal bar, colour-coded green/amber/red.
- New Lead Status Breakdown — side-by-side stage and health funnels for the last 7 and 30 days.
- Active Pipeline by Stage — proportional bar funnel for all unconverted leads.

**Nav bar:** `leads.html` was added to the navigation after Campaigns in:
- `Ritual Dashboard/dashboard/index.html` (static nav)
- `Ritual Dashboard/dashboard/targets.html` (static nav)
- `Ritual Dashboard/dashboard/assets/components.js` (shared React component — covers all other pages)

---

## 2. All-classes customer scraper — API replacement analysis

### Background

`momence_class_customers_scrape_1 all.py` (Step 7 in `Run_Momence_Chain.bat`) is a long-running Selenium job (60–80 minutes, ~470 classes) that visits each class page individually and scrapes the customer roster.

A transient network timeout to localhost (ChromeDriver) recently caused the cookie reload step to fail mid-run.

### What the scraper currently collects

| Field | Source |
|---|---|
| Class Number (session ID) | `href` containing `/sessions/{id}` |
| Class Name | Class page title |
| Customer Name | DOM: `span.sc-1ta22rh-0` |
| Signup Time | DOM: `div.sc-1pvjkb7-0` |
| Payment Method | DOM: `div.sc-13fi9me-0.doAyKG` |

Output file: `Momence_class_customers_all_*.csv`

### Can the API replace it?

**Short answer: yes, completely** — and with additional fields the scraper does not capture.

The documented Momence v2 API endpoint `GET /api/v2/host/sessions/{id}/bookings` returns:

| API field | Maps to scraper field |
|---|---|
| URL parameter `{id}` | Class Number ✅ |
| `member.firstName` + `member.lastName` | Customer Name ✅ |
| `createdAt` | Signup Time ✅ |
| `member.email` | *(not in scraper — bonus field)* |
| `checkedIn` | *(not in scraper — bonus field)* |
| `cancelledAt` | *(not in scraper — bonus field)* |
| Payment Method | ❌ not in API response |

See `Momence_API_v2_Reference.md` for full endpoint documentation.

### The Payment Method question — resolved

Payment Method is absent from the v2 API bookings response. However, this turns out not to be a blocker, because `master_bookings.csv` **already contains Payment Method and Membership used** as columns 7 and 8.

`master_bookings.csv` is populated by `Momence_bookings_update.py`, which downloads the **Session Bookings Report** from `https://momence.com/dashboard/32083/reports/session-bookings` — a purpose-built Momence CSV export. This runs as Step 4 in the chain, independently of the customer scraper.

Consequently, the Payment Method that `momence_class_customers_scrape_1 all.py` laboriously extracts from each class page's DOM is already present in `master_bookings.csv`, sourced via the report download. The scraper's capture of it is entirely redundant.

### What each source uniquely provides

| Field | master_bookings.csv | All-classes customer scraper | API replacement |
|---|---|---|---|
| Session / Class Number (ID) | ❌ | ✅ | ✅ (URL parameter) |
| Customer Email | ✅ | ❌ | ✅ (bonus) |
| Customer Name | ❌ | ✅ | ✅ |
| Signup Time | Sale Date (approximate) | ✅ `createdAt` | ✅ `createdAt` |
| Payment Method | ✅ | ✅ (redundant) | ❌ (already in master_bookings) |
| Membership used | ✅ | ❌ | ❌ (already in master_bookings) |
| Check-in status | ✅ (via No Shows report) | ❌ | ✅ (bonus) |
| Cancellation | ✅ Cancelled column | ❌ | ✅ `cancelledAt` (bonus) |

### Next step

The all-classes customer scraper (`momence_class_customers_scrape_1 all.py`) can be replaced with a pure `requests`-based API loop calling `GET /api/v2/host/sessions/{id}/bookings` for each session ID. This would:

- Eliminate the ChromeDriver/cookie timeout failure mode entirely.
- Reduce runtime from 60–80 minutes to a few minutes.
- Remove dependency on CSS selectors that break when Momence deploys updates (see `Momence_data_scraping_wisdom.md` §3).
- Yield richer output: email, check-in, and cancellation status in addition to name and signup time.
- Use the same OAuth 2.0 authentication already implemented in `momence_api_client.py`.

The list of session IDs to process comes from `momence_all_classes_*.csv` (produced by Step 6, `extract_all_classes_1.py`), which is unchanged.

---

## Relevant existing documentation

| File | Contents |
|---|---|
| `LEADS_SCRAPER.md` | Leads scraper design, output schema, and known data quirks |
| `Momence_API_v2_Reference.md` | Full v2 API endpoint reference including session bookings |
| `Momence_data_scraping_wisdom.md` | Comprehensive guide: auth, selectors, error handling, traps, lessons learned |
| `momence_api_client.py` | Python API client with OAuth 2.0 authentication |
| `momence_class_customers_all_1.py` | The scraper being considered for replacement |
| `Momence_bookings_update.py` | Populates master_bookings.csv via Session Bookings Report download |
