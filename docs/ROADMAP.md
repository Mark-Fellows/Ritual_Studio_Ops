# Ritual Studio Ops — Roadmap

Backlog of cross-project technical and security work. Newest items at the top of
each section. Created 2026-06-05.

---

## Security

### Enable RLS on 12 exposed tables — **Critical, Open**

- **Logged:** 2026-06-05
- **Detail:** 12 tables in the shared Supabase project (`rfjygyqijwgkmxboddup`)
  have Row Level Security disabled and are readable/writable by anyone holding
  the anon key. Affects all four apps at once.
- **Tables:** `cover_requests`, `whatsapp_monitor_runs`, `whatsapp_messages`,
  `cover_candidates`, `trainee_enrollments`, `trainee_bookings`, `timeslots`,
  `system_config`, `training_courses`, `discipline_mappings`,
  `whatsapp_channels`, `cover_notifications`.
- **Action:** Enable RLS table-by-table with appropriate policies (see
  `SECURITY-RLS-DISABLED-2026-06-05.md`). Must be tested in the parallel-run
  window — enabling RLS without policies blocks all access.
- **Owner:** TBD
- **Reference:** `docs/SECURITY-RLS-DISABLED-2026-06-05.md`

---

## Data quality

### Duplicate teacher rows — **Open**

- **Logged:** 2026-06-05
- **Detail:** Some teachers have more than one row in `teachers` (e.g. Rose
  Lamont, Angel Dixon). This makes name-based matching to Momence data
  ambiguous and risks split/duplicated grade data. Noted during the 2026-06-05
  grade import (the Rose Lamont yoga fill landed on the all-zero duplicate row).
- **Action:** Identify and merge duplicate teacher records; add a uniqueness or
  dedup safeguard.
- **Owner:** TBD

### Grade key inconsistency (`mat` vs `mat_pilates`) — **Open**

- **Logged:** 2026-06-05
- **Detail:** `teachers.grades` JSON uses both the legacy `mat` key and the
  canonical `mat_pilates` key across different rows. The canonical taxonomy
  (`disciplines.code`) is `mat_pilates`. Mixed keys complicate reads and writes.
- **Action:** Normalise all grade JSON to the canonical discipline codes and
  drop the legacy `mat` key once the app reads only `mat_pilates`.
- **Owner:** TBD
