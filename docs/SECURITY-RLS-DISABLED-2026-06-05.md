# Security Issue — Row Level Security disabled on 12 tables

**Logged:** 2026-06-05
**Severity:** Critical
**Project:** Supabase `rfjygyqijwgkmxboddup` (shared by all four Ritual apps)
**Status:** Open — remediation not yet applied
**Found during:** Teacher grade import (Momence last-3-months discipline backfill)

---

## Summary

Twelve tables in the shared Supabase project have Row Level Security (RLS)
**disabled**. These tables are fully exposed to the `anon` and `authenticated`
roles used by the Supabase client libraries. In practice this means **anyone
holding the project's anon key — which ships in the front-end of every Ritual
web app — can read or modify every row in these tables.**

Because the database is shared, the exposure spans Teacher Management, Cover
Management, Campaigns, Momence data and the Dashboard simultaneously.

## Affected tables

| Table | Rows | Owner area | Notable exposure |
|---|---:|---|---|
| `cover_requests` | 103 | Cover Management | Operational cover request records |
| `whatsapp_monitor_runs` | 420 | Cover Management | Monitoring/run history |
| `whatsapp_messages` | 220 | Cover Management | Captured WhatsApp message content |
| `cover_candidates` | 21 | Cover Management | Candidate matches per request |
| `trainee_enrollments` | 20 | Teacher Management | Trainee enrolment records |
| `trainee_bookings` | 12 | Teacher Management | Trainee booking records |
| `timeslots` | 12 | Teacher Management | Timeslot reference |
| `system_config` | 8 | Cover Management | Configurable thresholds/defaults |
| `training_courses` | 6 | Teacher Management | Course catalogue |
| `discipline_mappings` | 6 | Cover Management | Superseded by `disciplines` |
| `whatsapp_channels` | 5 | Cover Management | Monitored channel list |
| `cover_notifications` | 0 | Cover Management | (empty, still exposed) |

## Risk

- **Confidentiality:** WhatsApp message content and trainee/booking records are
  readable by anyone with the anon key.
- **Integrity:** Rows can be inserted, updated or deleted by any client. A
  malicious or buggy caller could corrupt cover requests, config thresholds or
  trainee bookings.
- **Blast radius:** Shared database — every app is affected at once.

## Recommended remediation

Enabling RLS **without policies blocks all access** to a table, which will break
any app currently relying on open access. So this must be done table-by-table,
each with appropriate policies, and tested in the parallel-run window.

Step 1 — enable RLS (do **not** run blindly; pair each with policies):

```sql
ALTER TABLE public.training_courses      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trainee_enrollments   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.timeslots             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trainee_bookings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_config         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_channels     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discipline_mappings   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cover_requests        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cover_candidates      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cover_notifications   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_monitor_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whatsapp_messages     ENABLE ROW LEVEL SECURITY;
```

Step 2 — for each table, add policies that mirror how it is actually used
(e.g. `authenticated` read where appropriate, writes restricted to service-role
or the relevant role per the RBAC matrix in `RBAC-MATRIX.md`). Reference the
existing RLS-enabled tables (`teachers`, `momence_sessions`) for the established
pattern, and watch for the RLS recursion trap documented in the Teacher
Management Prompt Guide.

Step 3 — verify with `SELECT` as anon vs authenticated, and confirm each app
still functions during the parallel run before cutover.

## Notes

- `discipline_mappings` is already superseded by `disciplines`; consider
  retiring rather than securing it.
- This issue was surfaced automatically by the Supabase advisor
  (`rls_disabled`, priority 1) during the 2026-06-05 grade import.

## Doc reference

- See `ROADMAP.md` → "Security: enable RLS on 12 exposed tables".
