# Ritual Studio Ops — Lessons Learned

Consolidated hard-won knowledge from all four projects. Every lesson follows the same structure:

**Problem** — what went wrong or surprised us
**Cause** — why it happened
**Fix** — what resolved it
**Applies to** — which projects / layers are affected

New lessons are appended at the bottom under their date. Do not edit existing entries.

---

## From Teacher Management — Seven Critical Technical Constraints

Source: `Ritual_Teacher_App_Prompt_Guide.md` (Phase 2, Prompt 2A and surrounding context)

---

### L-TM-01 — navigator.locks deadlock with multiple tabs

**Problem:** Opening the TM app in more than one browser tab causes a deadlock. The app hangs indefinitely.

**Cause:** The Supabase JS client uses `navigator.locks` internally for session management. When two tabs share the same origin, they lock each other out.

**Fix:** Never use the Supabase JS client for data queries. Use direct `fetch()` calls to the Supabase REST API with a cached JWT token. The client (`sbClient`) is used *only* for auth state (`onAuthStateChange`). All queries go through `dbGet()`, `dbPost()`, `dbPatch()`, `dbDelete()` wrappers that build headers from the cached session.

**Applies to:** All HTML/JS apps that share the Supabase project (TM, CM dashboards, RSO merged app).

---

### L-TM-02 — Variable name conflict: do not call the client "supabase"

**Problem:** Naming the Supabase client `supabase` causes a conflict with `window.supabase` injected by the CDN script tag.

**Cause:** The Supabase JS CDN sets `window.supabase`. Declaring `const supabase = createClient(...)` silently overwrites it or conflicts, producing unpredictable auth failures.

**Fix:** Always name the client `sbClient`. This is a hard convention in this codebase. Every `createClient()` call must assign to `sbClient`.

**Applies to:** All HTML/JS apps using the Supabase CDN.

---

### L-TM-03 — Never call getSession() after initial load

**Problem:** Calling `sbClient.auth.getSession()` anywhere other than the initial setup causes session retrieval to fail intermittently.

**Cause:** `getSession()` triggers internal locks. After `onAuthStateChange` fires, the session is already available and should be cached.

**Fix:** Cache the session object inside `onAuthStateChange` as `cachedSession`. Reference `cachedSession` everywhere else. Never call `getSession()` after initial setup.

**Applies to:** All HTML/JS apps in this project.

---

### L-TM-04 — RLS policies must not reference the same table they protect (recursion)

**Problem:** An RLS policy that does `SELECT FROM teachers WHERE user_id = auth.uid()` on the `teachers` table causes an infinite loop and times out.

**Cause:** RLS policies on a table are evaluated *during* any query on that table, including the sub-query inside the policy itself.

**Fix:** RLS policies that need to look up the current user's role must query a *different* table (e.g. `user_profiles`), never the table being protected.

**Applies to:** All RLS policies across the shared Supabase project.

---

### L-TM-05 — Edge Functions: Verify JWT must be OFF for the create-user function

**Problem:** The `create-user` Edge Function (which provisions new users) returns 401 when called during onboarding.

**Cause:** Verify JWT is ON by default. The function is called before the caller has a valid JWT (they are being created). Enabling Verify JWT means the function validates an auth token that does not yet exist.

**Fix:** Set Verify JWT to OFF specifically for the `create-user` function. All other Edge Functions keep it ON.

**Applies to:** Supabase Edge Functions in this project.

---

### L-TM-06 — Import Supabase JS from esm.sh, not cdn.jsdelivr.net

**Problem:** Importing Supabase JS from jsdelivr causes module resolution failures in some browser/network combinations.

**Cause:** The jsdelivr CDN does not serve ES module format correctly for all Supabase versions.

**Fix:** Use `https://esm.sh/@supabase/supabase-js@2` as the import source. This is the only tested-and-working CDN for this project.

**Applies to:** All HTML/JS apps importing the Supabase client.

---

### L-TM-07 — Version every file; never overwrite the canonical copy in place

**Problem:** A working version of the app was overwritten during an editing session, losing stable state.

**Cause:** Editing the single HTML file in place without versioning means there is no rollback point.

**Fix:** Every substantive edit produces a new version file (`ritual-teacher-management31.html` → next edit becomes `ritual-teacher-management32.html`). The highest numbered file is the working copy. Never delete lower versions until the higher version is confirmed stable.

**Applies to:** All single-file HTML/JS apps in this project (TM app, CM dashboards, RSO merged app).

---

## From Teacher Management — Bug Root Causes

Source: `CHANGELOG-2026-04-05-teacher-management.md`

---

### L-TM-08 — Modal close must not clear state before the handler reads it

**Problem:** Rejecting a trainee booking sent a `PATCH trainee_bookings?id=eq.null` request to Supabase.

**Cause:** The modal close routine cleared `pendingRejectBookingId` before the rejection handler had read it. The handler then read `null`.

**Fix:** Preserve all state variables needed by a handler *before* closing the modal. Do not clear state in the close routine if any pending handler still needs it.

**Applies to:** Any modal/action pattern in HTML/JS apps.

---

### L-TM-09 — REST responses may not include all columns; do not filter on absent columns

**Problem:** Filtering teachers by `user_id` in a REST query returned 400 errors.

**Cause:** Some columns (including `user_id`) are not exposed in the REST response by default if the RLS policy does not permit them or if they are not in the select list.

**Fix:** Check which columns are present in a `GET /rest/v1/teachers?select=*` response before constructing filters on them. Use in-memory arrays as fallback when column is absent from REST response.

**Applies to:** All Supabase REST API queries.

---

### L-TM-10 — Defensive sign-in: surface auth/network failures explicitly

**Problem:** Auth failures (wrong password, network error) produced a blank or hung UI with no feedback.

**Cause:** The sign-in handler did not catch or display errors from `sbClient.auth.signInWithPassword()`.

**Fix:** Wrap sign-in in try/catch and display the error message to the user. Added in v29 (now v31). Always show a human-readable error on sign-in failure.

**Applies to:** RSO merged app (carry forward from TM v31).

---

## From Cover Management — Design Decisions and Traps

Source: `Ritual_Cover_Management/ARCHITECTURE.md`

---

### L-CM-01 — Use JSONB arrays for multi-value fields, not delimited strings

**Problem:** Storing multiple class times as a comma-delimited string (`"06:15, 09:15"`) makes querying and filtering unreliable.

**Cause:** SQL `LIKE` on a string field cannot reliably filter individual values from a comma list.

**Fix:** Store as JSONB arrays (`["06:15", "09:15"]`). PostgreSQL JSONB indexing supports `WHERE times @> '["06:15"]'`. Dashboard iterates the array for display.

**Applies to:** All multi-value fields in CM and RSO schema: times, studios, disciplines, dates.

---

### L-CM-02 — estimated_class_count is TEXT, not INTEGER

**Problem:** When a teacher's message is ambiguous, there is no valid numeric count to store.

**Cause:** The NLP parser returns `"?"` for ambiguous messages, which cannot be stored as an integer without a separate null-handling path.

**Fix:** Store `estimated_class_count` as `TEXT`. Supports both `"4"` and `"?"` without NULL complexity. Frontend displays `"4 classes"` or `"unclear"`.

**Applies to:** `whatsapp_messages.estimated_class_count` in CM schema.

---

### L-CM-03 — Deduplication key uses parsed teacher name, not raw WhatsApp sender

**Problem:** The same cover request appearing from two different WhatsApp users (e.g. a forward) was inserted twice.

**Cause:** The dedup key was the raw `sender` field from WhatsApp, which differs per forwarding user.

**Fix:** Use the teacher name *extracted by the NLP parser* from the message content as the dedup key. This correctly identifies the same teacher's message regardless of who forwarded it.

**Applies to:** `cover_processor.py` deduplication logic.

---

### L-CM-04 — WhatsApp Web DOM selectors break without warning

**Problem:** The scraper stopped extracting messages for several days in February 2026. No error was logged; it simply returned zero results.

**Cause:** WhatsApp updated their web DOM CSS classes. The selectors (`data-pre-plain-text`, `data-testid="selectable-text"`) silently returned no matches.

**Fix:** Maintain a tiered selector strategy: Tier 1 href/icon selectors, Tier 4 JavaScript regex fallback. Monitor the batch log for zero-message runs. Never treat a zero-result run as success without a warning.

**Applies to:** `whatsapp_monitor.py`, any Selenium/Playwright scraping against WhatsApp Web.

---

### L-CM-05 — Quoted message detection is heuristic; do not over-engineer it

**Problem:** Attempts to use CSS selectors for quoted/threaded messages were brittle.

**Cause:** WhatsApp Web's quoted message DOM structure changes frequently.

**Fix:** Use heuristic text analysis: if the first line of a message is short (<40 chars), no special characters, and the second line starts with a capital, treat the first line as the quoted sender. Accuracy is ~95% for typical messages. Maintain a teacher name whitelist as a secondary check.

**Applies to:** `whatsapp_monitor.py`, `extract_quoted_message_info()`.

---

### L-CM-06 — Allow NULL foreign keys for unresolved teacher names

**Problem:** New teachers who message before being added to the `teachers` table would cause the insert to fail if teacher_id is NOT NULL.

**Fix:** Allow `NULL` for `requesting_teacher_id`, `offering_teacher_id`, etc. Store the raw extracted name in `*_teacher_name_raw`. Admin reviews unresolved records in the dashboard. Insert always succeeds; resolution happens separately.

**Applies to:** All cover-related tables with teacher references.

---

### L-CM-07 — anon_read_teacher_names RLS policy leaks PII — replace in Phase 1

**Problem:** The current `anon_read_teacher_names` policy on the `teachers` table allows unauthenticated callers to read all teacher columns including personal contact details.

**Cause:** The CM dashboards used anon keys for read access during development. The policy was added to support this.

**Fix (Phase 1):** Remove `anon_read_teacher_names` and replace with a column-restricted `teacher_directory` VIEW that exposes only `id, first_name, last_name`. Do both atomically in the same migration with a rollback script. After Phase 2 the CM dashboards are authenticated and no anon read path is needed.

**Applies to:** Phase 1 migration; any code that currently relies on anon teacher reads.

---

## From Momence_data — Scraper Constraints

Source: `Momence_data_scraping_wisdom.md` (consolidation pending MFPL OneDrive mount)

*Full scraping wisdom to be copied here from `services/momence/docs/` once the MFPL OneDrive is mounted and the two copies are consolidated. Key known constraints are noted below.*

---

### L-MD-01 — Momence rate limit: ~100 requests per minute

**Problem:** Batch API calls to Momence v2 fail with 429 errors when called too quickly.

**Cause:** Momence enforces a rate limit of approximately 100 requests per minute on their API v2.

**Fix:** Add a sleep/throttle between API calls. The API client must respect this limit. Phase 7 initial historical backfill will take several hours due to 55,000+ sessions and 500,000+ bookings.

**Applies to:** `momence_api_client.py`, Phase 7 sync scripts.

---

### L-MD-02 — Selenium scraper run time: 90–110 minutes; do not overlap runs

**Problem:** Running two scraper chain instances simultaneously causes session conflicts and incomplete data.

**Fix:** The Task Scheduler run at 02:00 Brisbane must have a minimum gap. Do not trigger manual runs while a scheduled run is in progress. The chain has checkpoint/resume so a failed run can be restarted safely.

**Applies to:** `Run_Momence_Chain.bat`, Windows Task Scheduler configuration.

---

### L-MD-03 — Momence cookie authentication requires periodic manual re-login

**Problem:** The Selenium scraper loses its session cookie every few weeks and produces zero results silently.

**Fix:** Monitor the batch log for authentication failure messages. When the cookie expires, a one-time manual login to Momence Web is required to refresh the session. This is a known limitation of cookie-based auth.

**Applies to:** Momence Selenium scraper chain.

---

## From the Merger — New Lessons

---

### L-MG-01 — Two copies of the same document will diverge; consolidate immediately

**Problem:** Two copies of the Momence scraping documentation (one in Momence_data, one in Ritual Dashboard) had already diverged by Phase 0.

**Fix:** Phase 0 consolidation is non-negotiable. After consolidation, update DOCS_INDEX to point to the single canonical copy and mark the other as `superseded`. Never create a second copy of an existing document.

**Applies to:** All documentation across the four projects.

---

### L-MG-02 — The sys.path.insert hack in CM stage 1 is fragile

**Problem:** `stage1/momence_teacher_sync.py` uses `sys.path.insert(0, _MOMENCE_DIR)` to import `momence_api_client`. If the MFPL OneDrive path changes or is unavailable, the import silently fails.

**Fix (Phase 3):** After Momence code moves to `services/momence/`, replace with a proper Python package import: `from services.momence.momence_api_client import MomenceAPIClient`. The CM project keeps its own copy of the API client during the parallel-run period as rollback insurance.

**Applies to:** `Ritual_Cover_Management/stage1/momence_teacher_sync.py`.

---

### L-MG-03 — Mermaid is a closed/retired studio

**Decision recorded 2026-05-21:** Mermaid is a closed Ritual studio location. It appears in Momence_data and the Dashboard because historical records reference it.

**Fix (Phase 1):** Include Mermaid in the `studios` reference table with `is_active = false`. Do not remove historical records that reference it. All new cover requests, teacher availability, and class records should reference only active studios.

**Applies to:** Phase 1 `studios` table design; CM NLP parser ACTIVE_STUDIOS list; Dashboard filters.

---

### L-MG-04 -- Write tool truncates files on OneDrive mounts; use bash heredoc

**Problem:** The Write tool silently truncated files when writing to the mounted OneDrive share.

**Cause:** The sandboxed Linux environment writes to OneDrive shares via a FUSE-like mount. The Write tool buffers output and cuts off mid-stream for larger files. The truncation is silent -- no error is returned.

**Fix:** For any file that needs to be written or rewritten on an OneDrive mount, use a bash heredoc:
  cat > "/path/to/file" << 'EOF'
  ...content...
  EOF
Confirm the byte count with `wc -c` after writing. Use ASCII characters only in section headers (see L-MG-05).

**Applies to:** Any Write tool call targeting OneDrive mounts. Read and Edit tools are not affected.

---

### L-MG-05 -- UTF-8 box-drawing characters in files cause silent truncation on OneDrive

**Problem:** The `.env.template` file was written with Unicode box-drawing characters in section headers. The file was silently truncated at byte 0x803, mid-UTF-8 sequence.

**Cause:** The OneDrive FUSE mount does not correctly handle multi-byte UTF-8 sequences at certain file offsets, causing the write to stop mid-character.

**Fix:** Use ASCII characters only in any file written to an OneDrive mount. Replace box-drawing section headers with plain ASCII dashes. Confirmed working at 2343 bytes with all-ASCII content.

**Applies to:** `.env.template`, any documentation or configuration file written via bash heredoc to OneDrive mounts.

---

### L-MG-06 -- Test string matching must target the assignment operator, not just the substring

**Problem:** `test_phase3.py` check `"_MOMENCE_DIR" not in cfg` produced a false positive failure. The test failed when `_MOMENCE_DIR` appeared only in a comment in `config.py`, not as a variable assignment.

**Cause:** The check tested for substring presence anywhere in the file, including comments. `config.py` contained the comment `# Replaces the hardcoded _MOMENCE_DIR sys.path.insert in each stage file.` which matched the substring.

**Fix:** When testing that a hardcoded variable has been removed, match the assignment form, not the bare name:
  assert "_MOMENCE_DIR =" not in cfg and "_MOMENCE_DIR=" not in cfg
This correctly identifies a variable declaration while ignoring comments and prose that mention the name.

**Applies to:** All test scripts that check for removal of hardcoded variables or paths.

---

### L-MG-07 -- Desktop Commander cmd shell: `cd /d` fails with space-containing paths

**Problem:** Running `cd /d "C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops"` in a Desktop Commander cmd shell returned "The filename, directory name, or volume label syntax is incorrect."

**Cause:** The Desktop Commander shell does not correctly handle `cd /d` with a quoted path containing spaces in this Windows environment.

**Fix:** Never use `cd /d` for git operations from Desktop Commander. Instead, write a `.bat` file that uses the `git -C "path"` flag, which specifies the working directory as a git option rather than a shell working directory change:
  set RSO=C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Studio_Ops
  "%GIT%" -C "%RSO%" commit -m "message"
This avoids any `cd` operation entirely.

**Applies to:** All git operations run from Desktop Commander on this machine.

---

### L-MG-08 -- Phase-specific .bat files prevent stale commit messages

**Problem:** `rso_git.bat` was reused across phases. When Phase 3 work was committed, the bat file still contained the Phase 2 commit message, producing a misleading git log entry that had to be amended.

**Cause:** The batch file was updated for Phase 2 but not updated before the Phase 3 commit.

**Fix:** Write a new `.bat` file for each commit containing a phase-specific commit message. Never reuse a bat file with an old message. When a wrong message is committed, fix immediately with:
  "%GIT%" -C "%RSO%" commit --amend -m "correct message"
then run `git log --oneline -4` to confirm.

**Applies to:** All git commit batch files across the RSO project.

---

### L-MG-10 -- Both portal tiles link to the merged app, not to the legacy cover site

**Problem:** The Cover Dashboard portal tile was changed to link to `ritual-cover-management.pages.dev/cover_dashboard.html` after it appeared to be going to the wrong place.

**Cause:** The merged app (`ritual-studio-ops-v2.html`) defaults to the Teachers view, so clicking Cover Dashboard appeared to open Teacher Management. This was misread as a wrong URL, when the URL was correct but the wrong tab was shown.

**Fix:** Per `NAVIGATION.md` — both Cover Dashboard and Teacher Portal tiles correctly resolve to `./ritual-studio-ops-v2.html`. Add `#cover` to the Cover Dashboard href and read `window.location.hash` inside `onSignedIn` to call `switchView('cover')` after data loads. Never link a portal tile back to a legacy `ritual-cover-management.pages.dev` URL.

**Applies to:** `Ritual_Studio_Ops/app/index.html` tile hrefs; any future portal tiles that need to deep-link into the merged app.

---

### L-MG-11 -- Magic-link emailRedirectTo must be hardcoded to the production URL

**Problem:** Magic-link emails were delivered to `ritual-cover-management.pages.dev` (the legacy site) instead of the portal, so the auth code was never exchanged and login failed.

**Cause:** `emailRedirectTo` was set to `window.location.origin + window.location.pathname`. Supabase silently ignores this value if the domain is not in its Allowed Redirect URLs list and falls back to the configured Site URL. The Site URL had not been updated from the old cover management domain after the merger.

**Fix:** Hardcode `emailRedirectTo: 'https://ritual-studio-ops.pages.dev'`. Also update Supabase Auth → URL Configuration: set Site URL to `https://ritual-studio-ops.pages.dev` and add it to Allowed Redirect URLs.

**Applies to:** `Ritual_Studio_Ops/app/index.html` signInWithOtp call; any app that sends magic links after a domain migration.

---

### L-MG-09 -- Postgres partial index predicates must use only IMMUTABLE functions; CURRENT_DATE is not allowed

**Problem:** Creating an index with `WHERE deleted_at IS NULL AND end_date >= CURRENT_DATE` on the `teacher_absences` table failed with `ERROR: 42P17: functions in index predicate must be marked IMMUTABLE`.

**Cause:** Postgres requires all functions in a partial index predicate to be `IMMUTABLE` (same output for same input, forever). `CURRENT_DATE` is `STABLE` (consistent within a single transaction, but varies between transactions), so it is rejected.

**Fix:** Drop the `CURRENT_DATE` condition from the index predicate. Keep only truly immutable conditions such as `deleted_at IS NULL`. The date filter is applied at query-plan time anyway, so the index still correctly serves upcoming-absences queries — it just covers a slightly wider range of rows.

**Applies to:** All Supabase/Postgres partial index definitions across this project. Any attempt to use `now()`, `CURRENT_DATE`, `CURRENT_TIMESTAMP`, or `CURRENT_USER` in an index predicate will produce the same error.
