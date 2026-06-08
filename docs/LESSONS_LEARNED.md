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

---

### L-MG-12 -- Edit tool with non-ASCII characters in old_string/new_string truncates files on OneDrive mounts

**Problem:** After applying 11 Edit tool calls to `ritual-studio-ops-v2.html`, the file was truncated -- `</html>` was missing and the file ended mid-function. L-MG-04 stated "Read and Edit tools are not affected" by the OneDrive mount truncation issue, but this was incorrect for non-ASCII content.

**Cause:** One of the Edit operations contained a non-ASCII character (the graduation cap emoji, U+1F393, in the `old_string` parameter). The OneDrive FUSE mount mishandles multi-byte UTF-8 sequences during Edit operations, causing silent truncation at the point of the non-ASCII character.

**Fix:** Never include non-ASCII characters (emoji, box-drawing characters, curly quotes, en-dashes, etc.) in `old_string` or `new_string` parameters when editing files on OneDrive mounts. Replace non-ASCII characters with their HTML entity equivalents (e.g. `&#127962;` instead of the graduation emoji) before constructing the Edit call. If truncation has already occurred, reconstruct the file from git: use `git show HEAD:path/to/file` to recover the pre-edit version, identify the cut point, then append the missing tail.

**Applies to:** All Edit tool calls targeting files on OneDrive mounts. Update L-MG-04 caveat: Edit tool is safe for ASCII-only content only.

---

### L-MG-13 -- L-TM-01 applies to index.html too: never use sb.from() for data queries in the portal

**Problem:** Clicking the Cover Dashboard or Teacher Portal tiles in `index.html` opened `ritual-studio-ops-v2.html` in a new tab, which showed its login screen instead of the main app. The v2 app was never broken; the portal was.

**Cause:** `loadProfileAndPerms` in `index.html` used `sb.from('user_profiles')` and `sb.from('v_role_permissions_resolved')` -- Supabase JS client data queries. The Supabase JS client holds `navigator.locks` for the duration of these calls. When the v2 app opened in a second tab on the same origin, its Supabase client tried to acquire the same lock for `INITIAL_SESSION` processing and deadlocked. The v2 app fired `INITIAL_SESSION` with null and showed its auth screen.

**Fix:** Converted both queries in `loadProfileAndPerms` to direct `fetch()` REST calls using the `Authorization: Bearer` header built from `session.access_token`. The function signature changed from `(user)` to `(user, accessToken)` and the call site in `handleSession` passes `session.access_token`. The Supabase JS client in `index.html` is now used exclusively for `sb.auth.*` calls (auth state, signOut, signInWithOtp), which is the L-TM-01 requirement.

**Applies to:** `app/index.html`. Any future portal page that initialises a Supabase JS client and also uses `sb.from()` for queries will reproduce this deadlock when the v2 app is open in a second tab.

---

### L-MG-14 -- navigator.locks deadlock persists after L-MG-13 fix; resolve with a session relay page

**Problem:** After applying the Phase 6 fix (L-MG-13 -- converting `loadProfileAndPerms` from `sb.from()` to direct `fetch()` REST calls), the Cover Dashboard and Teacher Portal tiles in `index.html` still opened `ritual-studio-ops-v2.html` showing a login screen. The fix was correct but insufficient.

**Cause:** The Supabase JS v2 PKCE client in `index.html` holds the global `navigator.locks` session lock not only during `sb.from()` data queries (fixed in L-MG-13) but also for the entire duration of its `onAuthStateChange` listener callback. `index.html` registers an async listener that `await`s `handleSession` --> `loadProfileAndPerms`. Supabase awaits all registered listener callbacks before releasing the lock. During this window (typically 200-600ms after page load, and briefly again on each token refresh), the v2 implicit-flow Supabase client in the new tab cannot acquire the same lock to run its own `_initialize()` / `INITIAL_SESSION` processing. It either times out or returns null, triggering `onSignedOut()` and showing the auth screen.

**Fix:** Added `app/v2-relay.html`. The Cover Dashboard and Teacher Portal tile click handlers in `index.html` were changed from plain `<a>` links to JavaScript handlers that:
1. Call `sb.auth.getSession()` to obtain the current session.
2. Build a relay URL: `./v2-relay.html#access_token=...&refresh_token=...&token_type=bearer&view=cover`
3. Open the relay in a new tab via `window.open(..., '_blank', 'noopener')`.

The relay page creates a minimal Supabase client (`autoRefreshToken: false`, `detectSessionInUrl: false`) and calls `setSession()` to write the validated session to the shared localStorage key **before** v2.html loads. When v2.html loads after the relay's `window.location.replace()`, its Supabase client finds the session in localStorage during `INITIAL_SESSION` with no lock competition. For the Cover Dashboard, the relay appends `#cover` to the destination URL so `v2`'s `switchView('cover')` deep-link fires as expected.

**Fallback:** If `getSession()` fails or returns no session, the handler falls back to opening v2.html directly (the pre-Phase-7 behaviour). The relay gracefully handles a missing or invalid token by skipping `setSession()` and redirecting anyway.

**Pattern:** Whenever opening a same-origin Supabase app from another Supabase app that uses a different auth flow type (PKCE vs. implicit), always pass the session explicitly via a relay that calls `setSession()`. Do not rely on localStorage auto-detection when the opener tab may hold `navigator.locks`.

**Applies to:** `app/v2-relay.html` (new file), `app/index.html` (click handlers for `index.tile.cover_dashboard` and `index.tile.teacher_portal`). Any future portal tile that links to a same-origin Supabase app should use this relay pattern.


---

### L-MG-15 -- PKCE flow is fundamentally incompatible with email magic links in multi-tab contexts

**Problem:** After Phases 6 and 7 (navigator.locks fixes), magic links from email still never worked when clicked directly. Users had to manually copy the link URL and paste it into the portal tab. Sessions never persisted across visits. Root cause was not the v2 relay or locks -- it was the auth flow itself.

**Cause:** `flowType: 'pkce'` (Proof Key for Code Exchange) stores a randomly generated code verifier in `sessionStorage` of the tab that called `signInWithOtp()`. When the magic link is clicked in an email client, the OS opens it in a NEW browser tab (or a new window). That new tab has empty `sessionStorage` -- the verifier is gone. The Supabase PKCE exchange sends the `?code=XXXX` parameter to the server but the server requires the verifier to complete the exchange; without it the exchange returns a `code verifier mismatch` error and the flow silently returns to the email-entry page. The user's copy/paste workaround succeeded only because pasting the URL into the SAME tab that generated the OTP preserved `sessionStorage`.

**Fix:** Remove `flowType: 'pkce'` from `supabase.createClient()` in `index.html`. Supabase JS v2 defaults to implicit flow, where magic links contain `#access_token=XXXX&refresh_token=YYYY` directly in the URL hash. No verifier is required. `detectSessionInUrl: true` (already set) picks up the tokens from the hash in whatever tab the link opens in. Sessions persist in localStorage as normal.

**Update `onAuthStateChange`:** With PKCE, `SIGNED_IN` was a deliberate no-op because the session was not ready for REST calls at that moment (the PKCE exchange was still async). With implicit flow, `SIGNED_IN` fires with a fully valid session. Add `event === 'SIGNED_IN'` to the handled events alongside `INITIAL_SESSION` and `TOKEN_REFRESHED`. Use the existing `_authHandled` boolean flag to prevent double-processing if both `SIGNED_IN` and `INITIAL_SESSION` fire for the same magic-link redirect.

**Applies to:** `app/index.html` and any future portal page using `signInWithOtp()` for magic links. Never use `flowType: 'pkce'` with `signInWithOtp()` unless the login flow can guarantee the magic link is opened in the same browser tab (e.g., in-app link, same-origin redirect, custom scheme handler). For email magic links, always use implicit flow (default).


---

### L-MG-16 -- Relay using a Supabase JS client causes its own navigator.locks race

**Problem:** After Phase 7 and Phase 8, the Cover Dashboard and Teacher Portal tiles still opened v2 showing a login screen, despite the relay running and the portal's green debug panel showing repeated SIGNED_IN events.

**Cause:** The Phase 7 relay created a Supabase JS client inside the relay tab and called setSession(). In Supabase JS v2, setSession() acquires navigator.locks for the origin (shared across all tabs). This lock acquisition triggered a SIGNED_IN storage event in the portal tab, which caused the portal's onAuthStateChange listener to also briefly acquire the same lock. The v2 app (loading in the relay tab after window.location.replace) then had to wait for the portal to release the lock before its _initialize() could run. In some timing conditions, v2's INITIAL_SESSION fired before localStorage was in the expected state, resulting in a null session and the login screen.

The repeated SIGNED_IN events visible in the portal's debug panel (at 05:07:32, 05:07:36, etc.) were caused by the relay's setSession() writing to localStorage -- confirming the relay WAS running, but also confirming the lock contention.

**Fix (Phase 9):** Rewrote v2-relay.html to eliminate the Supabase JS client entirely:
1. First checks localStorage for the session already stored by the portal's Phase 8 implicit-flow login. If valid, redirects to v2 immediately with NO writes and NO lock acquisition.
2. If localStorage is empty or expired, decodes the access_token JWT payload (base64url, no libraries), constructs a minimal compatible session object, and calls localStorage.setItem() directly. This is synchronous and lock-free.
3. Redirects to ritual-studio-ops-v2.html with the appropriate hash (#cover or empty).

Added localStorage diagnostic logging to _openV2Relay in index.html (visible in green debug panel) to confirm session state at click time.

**Pattern:** Never create a Supabase JS client in an intermediate relay/trampoline page on the same origin as another Supabase client that may be active. Even a minimal client with autoRefreshToken:false triggers navigator.locks during _initialize() and setSession(). Use direct localStorage manipulation instead.

**Applies to:** app/v2-relay.html (rewritten), app/index.html (_openV2Relay diagnostic). Any future relay or trampoline page on this origin should use localStorage directly rather than a Supabase client.


---

### L-MG-17 -- Duplicate code block causes SyntaxError that silently disables all auth

**Problem:** After Phase 9, v2 still showed its login screen on every tile-click. The green portal debug panel confirmed the relay was working and the session was valid. The v2 console showed NO auth state change events -- just a single `Uncaught SyntaxError: Identifier 'pendingBookingPayload' has already been declared` at line 3318.

**Cause:** A 737-line duplicate of the TRAINEE PORTAL / CONFIRM BOOKING MODAL / APPROVALS VIEW / COURSE MANAGER etc. sections had been accidentally pasted into ritual-studio-ops-v2.html starting at line 3033. The duplicated block re-declared `let pendingBookingPayload = null;` (first declared at line 2559). JavaScript `let` and `const` cannot be re-declared in the same scope -- a SyntaxError is thrown synchronously before execution reaches the Supabase auth client initialisation. With no `onAuthStateChange` listener ever registered, `onSignedIn()` never ran, `#authScreen` (CSS default: `display:flex`) stayed visible permanently.

**Why it was hard to diagnose:** The green debug panel in the portal showed the relay running correctly and the session valid in localStorage. The relay itself succeeded. The issue was entirely inside v2 -- and only visible in v2's DevTools console, which showed no auth events at all (the decisive clue). All previous debugging focused on the relay and localStorage, not v2's own JavaScript.

**Fix:** Deleted lines 3033-3769 (737 lines) from ritual-studio-ops-v2.html. Confirmed no duplicate `let`/`const` declarations remain. File reduced from 3,995 to 3,258 lines.

**Diagnostic rule:** If v2's console shows no `Auth state change` events after a page load, the Supabase client never initialised. Check for SyntaxErrors first -- they silently abort all script execution. `let`/`const` re-declaration is the most common cause in large single-file apps.

**Applies to:** app/ritual-studio-ops-v2.html. Any large single-file app: always check for duplicate `let`/`const` declarations if the auth listener never fires.


---

### L-MG-18 -- Session relay cannot cross origins; direct link is correct for external apps

**Problem:** After Phase 10 fixed the v2 SyntaxError, the Cover Dashboard tile opened ritual-studio-ops-v2.html#cover instead of the legacy Ritual Cover Management app (ritual-cover-management.pages.dev/cover_dashboard.html).

**Cause:** During Phase 7, when the session relay was introduced for the Teacher Portal tile, the Cover Dashboard tile was also redirected through _openV2Relay('cover') on the assumption that v2 would eventually host the cover view. The tile href and its click listener were both changed to target v2. The legacy cover dashboard was never the intended destination after that change -- but the user expected it to remain so.

**Fix (Phase 11):** Restored the Cover Dashboard tile href to https://ritual-cover-management.pages.dev/cover_dashboard.html. Removed the click listener override. The <a> tag with target="_blank" rel="noopener" opens the legacy app directly. No session relay is needed or possible: localStorage is partitioned by origin, so a token written at ritual-studio-ops.pages.dev cannot be read at ritual-cover-management.pages.dev.

**Rule:** Session relay via localStorage only works within the same origin. Tiles that link to a different Cloudflare Pages project (different subdomain) must let the target app handle its own authentication. Never route a cross-origin tile through _openV2Relay().

**Applies to:** app/index.html. Any future portal tile linking to a different Pages project or external domain.


---

### L-MG-19 -- Edit tool truncated ritual-studio-ops-v2.html again on the OneDrive mount despite ASCII-only edits

**Problem:** While adding the Applicants view to app/ritual-studio-ops-v2.html (2026-06-01), a sequence of Edit-tool operations left the on-disk file truncated -- it ended mid-statement around the manual-cover-request fetch, with </script>, the footer and </html> missing. Byte-count reads from the mount were also unreliable (a truncated file reported the same byte count as the intact original).

**Cause:** The OneDrive FUSE mount mishandles buffered writes from the Edit/Write tools for this large single file (~286 KB), as in L-MG-04/L-MG-12. ASCII-only content did not prevent it here; the size and repeated edits appear to be the trigger.

**Fix:** Do not edit this file in place via the Edit tool on the OneDrive mount. Instead: (1) dump the intact version from git -- `git show HEAD:app/ritual-studio-ops-v2.html > /tmp/orig`; (2) apply all edits in the sandbox with a script (assert each old-string matches exactly once); (3) syntax-check the extracted <script> with `node --check`; (4) write back with `cp` and VERIFY (`wc -c` equals expected and `tail -1` contains </html>), retrying if not. This recovered the file cleanly (3372 lines, 295384 bytes).

**Diagnostic rule:** After any tool-based write to a large file on the OneDrive mount, always verify the tail contains the expected closing tag and the byte count grew as expected. Never trust a single wc read.

**Applies to:** All large single-file apps on the OneDrive mount (ritual-studio-ops-v2.html especially). Prefer the git-dump + in-sandbox edit + cp-and-verify workflow over direct Edit-tool edits.

---

### L-MG-20 -- Live RLS policies and schema can drift from the migration files; phase numbers collide across workstreams

**Problem:** During the 2026-06-02 audit, `user_profiles` was found to carry four developer-gated RLS policies (read-all / insert / update / delete) that exist in **no** migration file in either repo -- they had been applied directly to make the merged-app user-management UI work. Separately, "Phase 5" was being used for four unrelated things (merger parallel-run, Cover-Management user-admin feature, v2 build-iteration tag, and a 2026-05-09 auth sub-phase), making "roll out Phase 5" ambiguous.

**Cause:** Policies applied via the Supabase dashboard / ad-hoc `apply_migration` without writing a corresponding file; and four parallel workstreams each minting their own "Phase N" numbering.

**Fix:** Always verify live state with `pg_policies` / `pg_proc` / `to_regclass` before trusting a design doc or migration file. Record any out-of-band change as a parity migration (see `migrations/2026-06-02-user-profiles-admin-rls-backfill.sql`). For phase numbers, cite `docs/PHASE-NUMBERING.md` and prefer naming features explicitly over new "Phase N" labels.

**Applies to:** All projects on the shared Supabase project; all design/spec docs.

---

### L-MG-21 -- index.html working copy was silently truncated (pre-existing); recover from git HEAD, not the working tree or a same-day backup

**Problem:** During the RBAC work the working-tree `app/index.html` was found truncated to 82,552 bytes, ending mid-statement (`$confirmPw.addEven`) with an unclosed `<script>` -- it would not function if deployed. git HEAD held the intact 87,441-byte file. A same-day backup taken at the start of the session had already captured the truncated copy.

**Cause:** A prior session's Edit/Write truncation (same class as L-MG-19) left the working tree corrupted and uncommitted; it was never caught because nothing re-validated the file.

**Fix:** Confirmed the working copy was an exact byte-prefix of HEAD (pure truncation, no real edits) with `cmp`, then restored via `git show HEAD:app/index.html > app/index.html` before patching. Always validate large single-file apps after any tool edit (`node --check` on the inline script + a closing-tag/byte-count check), and prefer `git show HEAD:` over working-tree backups when a backup may itself be corrupt.

**Applies to:** index.html, ritual-studio-ops-v2.html, and any large single-file app on the OneDrive mount.

### L-MG-22 -- ritual-studio-ops-v2.html contains duplicate top-level function declarations; the later copy wins

**Problem:** Every user-management function (loadUserProfiles, sendUserInvite, deleteUser, updateUserRole, addNonTeacherUser) is declared twice in the single inline script -- once around line ~2300 (block A, dead) and once around ~3070 (block B, live). Function declarations do not throw on redeclaration, so the LATER definition silently wins; editing only block A would have no runtime effect.

**Cause:** A duplicated code block (same family as the L-MG-17 duplicate that caused a SyntaxError when it involved let/const).

**Fix:** When patching these functions, patch the block-B (later) copy, or patch both identically. Deterministic patchers should assert the expected occurrence count (1 vs 2) so a duplicate is never missed. Consider removing block A in a dedicated, tested cleanup.

**Applies to:** ritual-studio-ops-v2.html.

### L-MG-23 -- resolved_classes table rows have their own discipline field; always prefer it over the request-level discipline_code

**Problem:** The "Classes That Need Cover" table in cover_dashboard.html displayed the wrong discipline for some rows. A mixed-discipline request (e.g. Mat Pilates at 5:15am + Reformer at 6:15am and 7:15am) showed Mat Pilates for every row because the renderer called `disciplineLabel(r.discipline_code)` — a single scalar on the cover_request row — for all classes.

**Cause:** Two levels of discipline data exist on every resolved request: (1) `r.discipline_code` on the cover_request row, set by the NLP extractor to a single value (typically the first or most prominent discipline in the message); and (2) `c.discipline` on each resolved_classes record, sourced directly from Momence's session data and therefore accurate per-class. The table row renderer ignored the per-class Momence value and re-applied the request-level scalar to every row.

**Fix:** Use `c.discipline || r.discipline_code` in any per-class renderer — prefer the Momence class-level discipline; fall back to the request-level code only when absent.

**Applies to:** cover_dashboard.html resolved-classes table; any future renderer that iterates resolved_classes rows.

### L-MG-24 -- formatDate() already includes the weekday; do not also prepend c.weekday

**Problem:** The date cell in the resolved-classes table rendered as "Wed, Wed 3 Jun" — the weekday appeared twice.

**Cause:** `formatDate()` calls `toLocaleDateString('en-AU', { weekday: 'short', ... })` which already produces "Wed, 3 Jun". A separate `wd` variable was constructed from `c.weekday` and prepended, doubling the day name.

**Fix:** Drop the `wd +` prefix when `formatDate()` is used; the function is self-contained. If a raw day-of-week prefix is ever needed without a formatted date, do not use `formatDate()` — use a date formatter with no weekday option instead.

**Applies to:** cover_dashboard.html resolved-classes table date cell.
2026-06-08 | Dashboard c1_momence.js | Lite scrape keyed by Class Number (template ID), not session. The Momence "Teacher/Host" field on a recurring class template reflects the class owner, not the actual per-session teacher. Occupancy CSV (keyed date+class+studio) is the authoritative per-session teacher source and must take priority over the lite scrape in instructor resolution.
---

### L-MG-25 -- L-TM-08 recurred in submitPendingBooking: payload nulled before POST

**Problem:** Trainee bookings showed a success toast ("Booking request created (status: pending)") but no row was ever written to trainee_bookings. The coordinator could not see the booking. The trainee's "Booked Timeslots" view was empty.

**Cause:** submitPendingBooking() followed the exact L-TM-08 pattern. closeConfirmBookingModal() was called first, which set pendingBookingPayload = null. The dbPost() call immediately after received null as its payload. JSON.stringify(null) = "null"; PostgREST returned 2xx with an empty body, so no error was thrown and the success toast fired. No row was inserted.

Additionally, user_id (the auth user's UUID from cachedSession.user.id) was absent from the payload, so even a correctly-inserted booking would never match matchesBookingOwner() and the "Mine" label and "Only my bookings" filter would be broken.

**Fix:** In submitPendingBooking(), capture the payload into a local const and add user_id before calling closeConfirmBookingModal():
  const payload = { ...pendingBookingPayload, user_id: cachedSession?.user?.id || null };
  closeConfirmBookingModal();
  await dbPost('trainee_bookings', payload);

**Applies to:** ritual-studio-ops-v2.html submitPendingBooking(). Any modal-with-confirm pattern: always capture all state into a local variable before calling the close/clear routine.
