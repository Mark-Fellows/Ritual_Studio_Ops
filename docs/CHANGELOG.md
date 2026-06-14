# Ritual Studio Ops — Master Changelog

All significant changes to schema, code, configuration, and documentation across all four Ritual technology projects, in reverse chronological order.

Individual project changelogs are NOT the authoritative record from Phase 0 onwards — this file is. Add a one-line entry here first, then write detail in the project-level file if needed.

Format: `YYYY-MM-DD | Project | Summary | Files changed`

## 2026-06-12 | Portal | Persist login mode preference to localStorage (rmp_last_login_mode) so mobile users who prefer password login are not reset to magic link on every session expiry; v1.1.3 | app/index.html

## 2026-06-12 | Cover Management (legacy) | Edit modal: added editable raw_message textarea so admin can create or correct message text to improve NLP accuracy; field saved back to cover_requests.raw_message on Save & Approve | public/cover_dashboard.html

## 2026-06-12 | Cover Management (legacy) | Split-request feature: admin can split a multi-date/studio cover request into two or more independent child requests via checkboxes on the resolved-classes table; parent shown greyed with provenance badge; migration adds parent_request_id, is_split_parent, split_by, split_at to cover_requests; v1.3.33 | public/cover_dashboard.html, migrations/2026-06-12-request-split-columns.sql

## 2026-06-09 | Cover Management (legacy) | WhatsApp view: add green tick / red cross association indicator to Offer and Rejection rows — shows whether the message is linked to a cover request via linked_to_cover_request_id; v1.3.32 | public/cover_dashboard.html

## 2026-06-08 | Teacher Management | Applicants view: add Notes column showing first two lines of most recent notes in table view — Phase 6c | app/ritual-studio-ops-v2.html

## 2026-06-05 | Teacher Management | Grade backfill from Momence: set grade 25 in disciplines taught over the last 3 months (5 Mar–5 Jun 2026, community + cancelled classes excluded) for matched teachers, fill-only where no existing grade. 20 grades filled across 20 teachers (19 mat_pilates, 1 yoga); 54 existing grades left untouched. Also logged a critical RLS-disabled finding (12 tables) and created a roadmap. | teachers.grades (DB, project rfjygyqijwgkmxboddup), docs/SECURITY-RLS-DISABLED-2026-06-05.md, docs/ROADMAP.md

Data-only change to the shared teachers table — no app or schema change, no deploy (both legacy and merged apps read grades live). Scope built from momence_sessions: last three months, class_cancelled IS NOT TRUE, class_name NOT ILIKE '%community%'; class names mapped to the 5 canonical disciplines (yoga/barre/reformer/mat_pilates/yin). Teachers matched by case-insensitive first+last name. Fill rule: set 25 only where the discipline grade was 0 or missing (legacy 'mat' key treated as equivalent to 'mat_pilates'); any existing grade > 0 preserved. Not processed (no teachers row): Amy Landry, Samantha Barrie, Sophie Lamont, Tomer Leibovich, and the Ritual YTT/PTT student/graduate placeholders. Roadmap also notes duplicate teacher rows (Rose Lamont, Angel Dixon) and the mat/mat_pilates key inconsistency.

## 2026-06-03 | Teacher Management | Applicants view: Edit button per row (openEditApplicant + saveTeacher applicants[] patch); grade sort added to sort select when discipline filter active; discipline filter also resets grade sort when cleared | app/ritual-studio-ops-v2.html

## 2026-06-03 | Teacher Management | Applicants view: discipline filter, applied-date sort toggle, stronger applied-date font, sub-heading fix; fix applicant count always 0 in Management Suite button (renderActionButtons called before loadData populated applicants[]) | app/ritual-studio-ops-v2.html

## 2026-06-03 | RBAC unification (User Admin 5.0/5.1) | Merge the two authorization regimes onto the DB permission model; admin RPCs + RLS; v2/portal wired to per-user resolver -- DB APPLIED, app staged (NOT pushed) | migrations/2026-06-02-rbac-unification-backbone.sql, migrations/2026-06-02-user-admin-rpcs-and-rls.sql, migrations/2026-06-02-user-admin-harden-grants.sql, app/ritual-studio-ops-v2.html, app/index.html, app/_user-admin-5.2-overrides.snippet.js, docs/RBAC-MATRIX.md, docs/USER-ADMIN-BUILD-SPEC.md, docs/PHASE-NUMBERING.md, backups/rbac-2026-06-02/

Autonomous session. Goal: one authorization model. Previously the portal (index.html) was permission-driven (v_role_permissions_resolved) while the merged app (v2) used a hard-coded ROLES capability object. Unified on the DB permission model.

DB (shared project rfjygyqijwgkmxboddup; backed up first to backups/rbac-2026-06-02/, ROLLBACK.sql provided):
- BACKBONE (apply_migration rbac_unification_backbone_2026_06_02): +11 permission rows extending the catalogue to Teacher-Management features (teachers/grades/bookings/applicants parents + leaves) and admin.users.manage; leaf grants per RBAC-MATRIX (administrator + coordinator get the TM leaves; admin.users.manage to developer+administrator; teacher gets teachers.edit_own_availability; developer covered by the system.admin wildcard); new user_permission_overrides table (RLS, read-own); new per-user resolver v_user_permissions_resolved (wildcard + parent cascade, overrides layered, security_invoker); has_admin_users_manage() helper. Verified: permissions 26->37, developer resolves 37, administrator 29, no parent-cascade over-grant.
- RPCs + RLS (apply_migration user_admin_rpcs_and_rls_2026_06_02): admin_invite_user / admin_set_user_role / admin_set_user_permission / admin_remove_user (SECURITY DEFINER, permission-checked, self-protection); user_profiles writes switched from developer-only to has_admin_users_manage() (administrator can now manage users); admin write policies on user_permission_overrides and role_permissions. Guard tested: non-admin call -> 'Permission denied'.
- HARDENING (apply_migration user_admin_harden_grants_2026_06_02): pinned search_path on has_admin_users_manage(); revoked EXECUTE on the admin RPCs + helper from anon/PUBLIC, granted to authenticated. From the security advisor.
- DEFERRED: per-column RLS on teachers (grades/applicants/edit share one table; row-level RLS can't separate them) -- stays app-layer enforced; teachers keeps its permissive authenticated CRUD policies.

App (staged locally, NOT pushed -- a push auto-deploys all four apps):
- v2 (ritual-studio-ops-v2.html): loads v_user_permissions_resolved into resolvedPerms; new hasPerm() + rpc() helpers; settings/admin gate switched from can('canManageUsers') to hasPerm('admin.users.manage'); invite now attaches profile+role via signInWithOtp + admin_invite_user (Option A) -- previously invitees landed with no role; role-change and delete routed through admin_set_user_role / admin_remove_user (onclicks now pass user_id). node --check PASS.
- index.html: permission read swapped to v_user_permissions_resolved (per-user; identical result today, forward-compatible). RECOVERED from a pre-existing working-tree truncation first (see L-MG-21). node --check PASS.
- 5.2 (per-user override tree UI): delivered as app/_user-admin-5.2-overrides.snippet.js (validated, ready to integrate + browser-test); DB fully supports it.

PENDING for Mark: browser-test v2 + portal as developer AND administrator; integrate 5.2 snippet; commit (sandbox could not write .git/index.lock) and push to deploy. See docs/USER-ADMIN-HANDOVER-2026-06-03.md.

## 2026-06-02 | Documentation | Phase-numbering disambiguation + Phase 5 user-admin re-spec; record live user_profiles RLS drift -- docs only, no DB change | docs/PHASE-NUMBERING.md, docs/DOCS_INDEX.md, docs/LESSONS_LEARNED.md, Ritual_Cover_Management/PHASE-5-USER-ADMIN-DESIGN.md, migrations/2026-06-02-user-profiles-admin-rls-backfill.sql

Documentation-consistency pass. "Phase 5" was found to mean four different things across the docs (merger-programme parallel-run, Cover-Management user-admin feature, v2 build-iteration tag, and a 2026-05-09 auth sub-phase). Added docs/PHASE-NUMBERING.md as the canonical disambiguation and cross-referenced it from DOCS_INDEX.

Marked PHASE-5-USER-ADMIN-DESIGN.md superseded and prepended a revision notice: it targeted the now-legacy public/index.html (must not be edited per SOURCE_OF_TRUTH); its "turn RLS on" premise is stale (RLS enabled 2026-05-17); the 5.1 user-admin UI already shipped in the merged v2 app but WITHOUT the 5.0 security foundation it called non-negotiable. Verified live (read-only) that admin.users.manage, user_permission_overrides, v_user_permissions_resolved, has_admin_users_manage() and the admin RPCs do NOT exist; only v_role_permissions_resolved does.

Recorded live RLS drift: user_profiles carries developer-gated insert/update/delete policies present in no migration file. Captured in migrations/2026-06-02-user-profiles-admin-rls-backfill.sql (parity/documentation only; already live; not applied). Decision locked: admin.users.manage to be granted to both developer and administrator at launch. No build and no database changes made -- re-spec first.

## 2026-06-01 | Teacher Management | Public teacher applications: applicant intake model, Applicants review view, manual mobile verify, approve-and-provision, soft reject, duplicate flagging; 31 Asana applicants imported -- Phase 6 | app/ritual-studio-ops-v2.html, migrations/2026-06-01-teacher-applications.sql, Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Applications_Design.md

Adds a public teacher-application capability using a status flag on the shared teachers table (status: active | applicant | rejected) rather than a separate table.

Migration 2026-06-01-teacher-applications.sql (applied via Supabase MCP, additive only): adds status, experience_training, teaching_style, video_url, availability_text, located_text, cv_url, email_verified, phone_verified, applied_at, source, possible_duplicate, duplicate_notes, rejected_at, rejected_by to teachers; teachers_status_check constraint; idx_teachers_status and idx_teachers_email_lower; new application_otps table (RLS on, service-role only, email channel; whatsapp channel reserved); seeds system_config row whatsapp_new_teachers_invite_url. Existing 80 teachers backfilled to status='active' (verified: 0 non-active before import).

v2 app (ritual-studio-ops-v2.html, bumped to Phase 6): loadData now splits fetched rows into teachers (active) and applicants (status='applicant'); applicants are excluded from the sidebar, counts, allocation check and availability. New "New Applicants (n)" button in the Management Suite opens renderApplicantsView -- a table with email/mobile verified badges, possible-duplicate warning, grade-2 discipline pills, locations, CV/video link, and an expandable experience/teaching-style/availability panel. Actions: markApplicantVerified (manual email/mobile verify, audited), approveApplicant (gated on both verified; provisions a teacher login via the existing create-user Edge Function then sets status='active'), rejectApplicant (soft status='rejected', records rejected_at/by). All gated on canEditTeachers and WRITES_ENABLED.

Data import: 31 teacher applications from Recruitment.xlsx (Asana export, 2026 submissions only) inserted via Supabase MCP as status='applicant', email_verified=false, phone_verified=false, source='asana_recruitment_import'. Chosen disciplines set to grade 2; studios mapped to active locations (Mermaid dropped per L-MG-03); 2 flagged possible_duplicate; 3 surnames set to '(surname pending)'.

WhatsApp mobile verification is deliberately NOT automated (paused pending WhatsApp Business activation); mobile is verified manually by an administrator.

Public intake (built same day): app/apply.html (public, unauthenticated form + email-code step, no Supabase JS client). Edge Functions deployed via Supabase MCP with verify_jwt=false (no local source, per the create-user precedent): submit-teacher-application (validates, dedupe-checks, inserts applicant with grades=2, uploads CV, sends email OTP), verify-application-otp (confirms the email code, sets email_verified), approve-applicant (called by the v2 Approve action; reconciles the email-OTP auth user by setting password/role and upserting user_profiles). Private storage bucket teacher-cvs created (pdf/doc/docx, 1 MB; authenticated read policy) via migration 2026-06-01-teacher-cvs-bucket.sql. v2 Approve now calls approve-applicant and CV opens via a signed URL.

Email verification uses Supabase Auth email OTP (signInWithOtp/verifyOtp), which creates a pending auth user at submit; approve-applicant finalises it on approval. CONFIG REQUIRED before public launch: the Supabase email OTP template must expose {{ .Token }} so applicants receive a 6-digit code, and apply.html must be deployed to Pages and linked from the website. Added an admin 'Import applications (CSV)' button in the Applicants view: parses an Asana CSV export (multi-line Notes blob via a robust RFC4180 parser), auto-skips any email already present in the teachers table, and bulk-inserts the remaining rows as applicants (grades=2, mapped locations, source='asana_recruitment_import'). The import uses the Asana 'Created At' column as applied_at (form-submission date) and shows a post-import summary modal listing each applicant added with their date plus the skipped duplicates. The Applicants view also gained a From/To date-range filter on the application date, an A-Z / Z-A sort by given name, and a Clear button.

Note: during this edit the OneDrive mount truncated ritual-studio-ops-v2.html via the Edit tool (see L-MG-19); the file was rebuilt from git HEAD with edits re-applied in-sandbox and written back with a byte-count/closing-tag verification.

## 2026-05-29 | Ritual Studio Ops | Add Finance & Cashflow tile + cashflow dashboard -- Phase 6 | app/index.html, app/finance-cashflow.html, app/_headers, docs/PORTAL-DEVELOPER.md, docs/DOCS_INDEX.md

New tile "Finance & Cashflow" added to the Internal tools section of app/index.html (between Ritual Dashboard and Ritual Campaigns), opening a new same-origin dashboard app/finance-cashflow.html. Supports the "Fix Ritual cash flow" work.

The tile intentionally has NO data-perm attribute (visible to all signed-in users), following the Ritual Campaigns tile pattern: the code "index.tile.finance" does not exist in v_role_permissions_resolved (confirmed via Supabase MCP before the change), so adding data-perm would grey the tile for every user. No schema migration was made.

finance-cashflow.html (v1) is a self-contained, static, client-side dashboard - no Supabase, no live DB. It embeds the Xero Stripe-settlement actuals for Jul 2025 - Feb 2026 (cash-in) from the "Xero Backfill & Financial Model Update" session summary (25 Mar 2026) and provides: a KPI snapshot; an actuals chart comparing Stripe cash-in vs the overstated prior Momence sales figures; an editable-assumption 13-week rolling cashflow forecast (opening cash, monthly revenue + trend, instructor/rent/other-opex, AP, BAS, super) with a closing-balance line chart and negative-week shading; a week-by-week table; the data-quality flags (unexplained Xero Operating Expense bucket, unreconciled "Other Income", unknown opening balance, rent basis); and the outstanding-items checklist. Assumptions persist to browser localStorage only. Chart.js loaded from jsdelivr CDN. _headers updated with a no-cache rule for the new page.

Note: the page has no auth gate of its own yet - it inherits no protection beyond the obscurity of its URL. Decision pending on whether to gate it (portal magic-link auth) before exposing sensitive financials. Not yet deployed or committed -- pending review.

## 2026-05-28 | Cover Management (legacy) | NLP correction feedback loop — audit script, analyzer, few-shot injection | stage2/nlp_correction_audit.py, stage2/nlp_prompt_analyzer.py, stage2/nlp_parser.py, SCHEMA.md, DEVELOPER.md, setup_scheduled_tasks.ps1

Three new components close the loop between manual classification corrections (made via the dashboard Edit Classification form) and the NLP classifier.

nlp_correction_audit.py (daily 07:00): queries whatsapp_messages for rows where manual_type_override differs from message_type, upserts them into stage2/nlp_corrections.json, enforces a 25-active-entry cap (oldest excess entries marked superseded), and triggers the analyzer early if the cap is reached.

nlp_prompt_analyzer.py (Monday 07:10, or early trigger): loads active corrections, groups them by misclassification pattern, calls Claude (Haiku) for a meta-analysis, and writes a proposal markdown file to stage2/nlp_prompt_proposals/nlp_proposal_YYYY-MM-DD.md for manual review. Does not auto-modify the system prompt.

nlp_parser.py: new _load_active_corrections() method loads nlp_corrections.json at parser startup. _build_context() now accepts an active_corrections parameter and prepends human-verified few-shot examples to every Claude/Gemini API call, immediately improving classification without a prompt edit.

SCHEMA.md: documented manual_type_override, override_by, override_note, override_at columns on whatsapp_messages; added invariant note that message_type is written once by the NLP parser and never overwritten. DEVELOPER.md: added full NLP Correction Feedback Loop section covering architecture, json structure, 25-entry cap rationale, scheduled task details, and manual promotion workflow. setup_scheduled_tasks.ps1 and two .bat wrappers added for the new tasks.

## 2026-05-28 | Cover Management (legacy) | Dashboard v1.3.23 — Other tab, corrections filter, refresh fix, override_by audit trail | public/cover_dashboard.html, migrations/2026-05-28-add-override-by-whatsapp-messages.sql, stage2/nlp_parser.py

Four improvements to the legacy cover dashboard and supporting NLP.

Other tab: added a fifth message-type filter tab (Other) to the WhatsApp feed so messages classified as other are visible and filterable without navigating away.

Corrections filter: added a Corrections dropdown (All / Corrected only / NLP only) alongside the existing Sort filter so admins can quickly isolate messages that have been manually reclassified versus those still showing the original NLP result.

Refresh interval fix: the feed was refreshing every 60 seconds regardless of the value saved in Settings. startAutoRefresh() now reads refresh_interval from localStorage and restarts the timer whenever Settings are saved. Background refreshes no longer clear the container with a loading spinner or cause the page to jump — the scroll position is preserved on every background update.

override_by audit trail: the Edit Classification form now writes the admin's initials (from the admin_initials localStorage setting, up to 5 chars) to the new override_by column on whatsapp_messages. The correction indicator on each message card shows the initials alongside the original and corrected type. Migration 2026-05-28-add-override-by-whatsapp-messages.sql adds the column (applied to shared Supabase project rfjygyqijwgkmxboddup). NLP REJECTION prompt expanded with informal/brief decline phrases (Can't, Nope, Clash, Away too, etc.) and a context rule that short replies in a cover channel must be classified as rejection unless clearly unrelated to cover.

## 2026-05-28 | Ritual Studio Ops | Fix Cover Dashboard tile: restore link to legacy cover app -- Phase 11 | app/index.html

Cover Dashboard tile in index.html was opening ritual-studio-ops-v2.html#cover (the v2 Studio Ops cover view) instead of the legacy ritual-cover-management.pages.dev/cover_dashboard.html. The tile href and its click-listener override were both changed to v2 during Phase 7 when the session relay was introduced.

Fixes applied to app/index.html:
1. Restored tile href to https://ritual-cover-management.pages.dev/cover_dashboard.html.
2. Removed the click-listener override that called _openV2Relay('cover') -- no relay is needed because ritual-cover-management.pages.dev is a different origin and has its own authentication. The <a> tag with target="_blank" rel="noopener" opens the URL directly.
3. Updated the _openV2Relay comment block to clarify it now serves Teacher Portal only.

## 2026-05-28 | Ritual Studio Ops | Fix v2 always showing login screen: remove 737-line duplicate code block -- Phase 10 | app/ritual-studio-ops-v2.html

Root cause of v2 always showing its login/auth screen when opened via portal tiles: a 737-line duplicate block of JavaScript had been accidentally inserted into ritual-studio-ops-v2.html starting at line 3033. The duplicated block contained a second declaration of `let pendingBookingPayload = null;` (originally declared at line 2559). Because `let` cannot be re-declared in the same scope, the JavaScript engine threw an uncaught SyntaxError on page load, halting all script execution before the Supabase auth client could initialise. With no `onAuthStateChange` listener registered, `onSignedIn()` never ran, `#authScreen` (CSS default: `display:flex`) remained visible permanently, and the app appeared stuck on the login screen regardless of session state.

The duplicate block covered sections: TRAINEE PORTAL (LEGACY TM), BOOKING OWNER MATCH, TRAINEE AVAILABLE TIMESLOTS VIEW, TRAINEE BOOKINGS VIEW, RESOLVE TEACHER ID FOR CURRENT USER, CONFIRM BOOKING MODAL, APPROVALS VIEW, COURSE MANAGER, BACKFILL VIEW, TIMESLOT MANAGER, HELP MODAL, PASSWORD TOGGLES, USER MANAGEMENT (settings page). These sections already existed in the preceding 760 lines. The unique sections following the duplicate (ESCAPE KEY HANDLER, MANUAL COVER REQUEST) were preserved.

Fix: deleted lines 3033-3769 (737 lines) from ritual-studio-ops-v2.html. No duplicate `let`/`const` declarations remain. File reduced from 3,995 to 3,258 lines.

## 2026-05-28 | Ritual Studio Ops | Fix magic-link login and session persistence -- Phase 8 implicit flow | app/index.html

Root cause of all three reported symptoms (magic links always return to email-entry page when clicked; copy/paste workaround required; session never persists): `flowType: 'pkce'` in index.html's Supabase client. PKCE stores a code verifier in `sessionStorage` of the OTP-requesting tab. Email clients open magic links in a NEW tab with empty sessionStorage, so the PKCE code exchange always fails. The user's copy/paste workaround worked because pasting into the same tab preserved the verifier.

Fixes applied to app/index.html:
1. Removed `flowType: 'pkce'` from `supabase.createClient()` -- reverts to implicit flow, where magic links carry `#access_token=...&refresh_token=...` directly in the hash. Works in any tab.
2. Updated `onAuthStateChange` to include `SIGNED_IN` in the handled events (previously a deliberate no-op because PKCE required deferring to INITIAL_SESSION). With implicit flow SIGNED_IN fires with a complete session. `_authHandled` flag prevents double-processing if both SIGNED_IN and INITIAL_SESSION fire for the same redirect.
3. Re-enabled the green auth diagnostics panel (`div#auth-debug`, bottom-left of screen) to assist ongoing development.

The Phase 7 session relay (v2-relay.html) is retained as belt-and-suspenders for the navigator.locks race, but with implicit flow now in both index.html and v2, the relay is no longer the critical path. See L-MG-15 in LESSONS_LEARNED.md.

---

## 2026-05-28 | Ritual Studio Ops | Fix Cover Dashboard/Teacher Portal tiles still showing login screen -- Phase 7 session relay | app/v2-relay.html, app/index.html

Phase 6 fix (L-MG-13 -- removing sb.from() calls) was necessary but insufficient. The Supabase JS PKCE client in index.html holds navigator.locks during its INITIAL_SESSION listener execution (not only during data queries); the v2 implicit-flow client in the new tab cannot acquire that lock and fires INITIAL_SESSION with null.

Fix: added app/v2-relay.html. The Cover Dashboard and Teacher Portal tile click handlers in index.html now call sb.auth.getSession(), build a relay URL with the session tokens in the URL hash, and open the relay instead of v2.html directly. The relay calls setSession() (autoRefreshToken:false, detectSessionInUrl:false) to write the session to localStorage before v2 ever loads -- no lock race is possible. For the Cover Dashboard, the relay appends #cover so v2's deep-link switchView('cover') fires correctly. See L-MG-14 in LESSONS_LEARNED.md.

---

## 2026-05-28 | Ritual Studio Ops | Fix Cover Dashboard and Teacher Portal tiles opening login screen | app/index.html

Root cause: `loadProfileAndPerms` in `index.html` used `sb.from()` Supabase JS client calls for data queries, violating L-TM-01. These calls hold `navigator.locks`, blocking the v2 app from detecting its session when opened in a new tab on the same origin. Result: v2 app fired `INITIAL_SESSION` with null and showed its login screen.

Fix: converted both data queries (user_profiles lookup and v_role_permissions_resolved lookup) to direct `fetch()` REST calls using the session access token. The Supabase JS client in `index.html` is now used exclusively for auth state (`sb.auth.*`), as required by L-TM-01. See L-MG-13 in LESSONS_LEARNED.md.

---

## 2026-05-27 | Teacher Management | Teacher absence tracking — per-teacher panel, global view, on-leave sidebar pill, CRUD modal, soft-delete archive, five RLS policies; migration applied via Supabase MCP | app/ritual-studio-ops-v2.html, migrations/2026-05-27-teacher-absences.sql

---

## 2026-05-27 | Ritual Dashboard | Footer badge standard applied to all dashboard pages | 18 files in Ritual Dashboard/dashboard/ and Ritual Dashboard/

Added the standard copyable footer badge (`data-file-id="rso-file-footer"`) to all 18 eligible HTML files in the Ritual Dashboard folder. Badge shows logical file path, version, and description; click-to-copy enabled. Files: `dashboard/campaigns.html`, `courses.html`, `financial.html`, `fitness-passport.html`, `index.html`, `leads.html`, `marketing.html`, `membership-tracker.html`, `memberships.html`, `projects.html`, `sales-tracker-rds.html`, `settings.html`, `studio-ops.html`, `targets.html`, `asana_cleaner.html`, `membership_attendance.html`, `momence_pipeline_swimlane.html`, `skill-eval-review.html`.

---

## 2026-05-27 | Ritual Studio Ops | Portal & access fixes — Cover Dashboard deep-link, magic-link auth redirect, footer badge standard

**Cover Dashboard deep-link (`index.html` + `ritual-studio-ops-v2.html`):**
The Cover Dashboard portal tile was pointing to `./ritual-studio-ops-v2.html` with no hash, so the merged app always opened on the Teachers view. Per `NAVIGATION.md`, both portal tiles correctly resolve to the merged app — the fix was to add `#cover` to the Cover Dashboard tile href and add a three-line hash check in `onSignedIn`: `if (window.location.hash === '#cover') switchView('cover');`. Teacher Portal tile unchanged at `./ritual-studio-ops-v2.html`.

An earlier incorrect intermediate fix had linked the tile to `https://ritual-cover-management.pages.dev/cover_dashboard.html` (the legacy read-only site). That link was reverted.

**Magic-link `emailRedirectTo` (`index.html`):**
`emailRedirectTo` was `window.location.origin + window.location.pathname`. When the Supabase Site URL was still set to `ritual-cover-management.pages.dev` (not yet updated after the merger), Supabase ignored the dynamic value and sent magic-link emails to the wrong domain. Fixed to hardcoded `'https://ritual-studio-ops.pages.dev'`. Supabase Auth → URL Configuration → Site URL and Allowed Redirect URLs must also be updated to `https://ritual-studio-ops.pages.dev`.

**Footer badge standard (all 7 portal pages):**
All `data-file-id="rso-file-footer"` divs across all apps had `pointer-events:none`, making the filename unselectable and uncopable. Replaced with `cursor:pointer; user-select:text;` and added an `onclick` click-to-copy handler (copies path to clipboard, briefly shows "Copied!"). `cover_dashboard.html` footer now includes the version string `v1.3.22`.

Files: `Ritual_Studio_Ops/app/index.html`, `Ritual_Studio_Ops/app/ritual-studio-ops-v2.html`, `Ritual_Cover_Management/public/cover_dashboard.html`, `Ritual_Cover_Management/public/index.html`, `Ritual_Cover_Management/public/studio_timetable.html`, `Ritual_Cover_Management/public/teacher_portal.html`, `Ritual marketing/campaign-planning.html`

---

## 2026-05-27 | Teacher Management | Teacher absence tracking implemented — per-teacher panel, global Absences view, on-leave sidebar pill, availability banner, soft-delete archive, five RLS policies; migration applied via Supabase MCP

Files: `Ritual_Teacher_Management/ritual-teacher-management31.html`, `Ritual_Teacher_Management/migrations/2026-05-26-teacher-absences.sql`, `Ritual_Teacher_Management/Ritual Teacher Management/Teacher_Absences_Design.md`

---

## 2026-05-22 | Ritual Studio Ops | Manual cover request entry — v2 app, Edge Function, schema

New feature: administrators and coordinators can now manually create a cover request from the Cover Requests tab without it going through the WhatsApp pipeline. Handles privately messaged requests.

**Schema (applied via Supabase MCP):** `cover_requests.source TEXT DEFAULT 'whatsapp'` added. Manual entries carry `source = 'manual'`; existing WhatsApp pipeline records keep the default.

**Edge Function:** `parse-cover-request` deployed to Supabase (project rfjygyqijwgkmxboddup). Accepts raw message text plus teacher/discipline/studio context. Calls Claude Haiku via Anthropic API. Returns structured fields (teacher name, date, time, class name, studio, discipline, coverage type) and a list of clarifying questions for anything ambiguous or missing. JWT-verified; uses ANTHROPIC_API_KEY from Supabase secrets.

**App v2 (`ritual-studio-ops-v2.html`):**
- Version comment and build stamp updated from v1/Phase 4 to v2/Phase 5.
- "New Manual Request" button added to Cover Requests tab header (visible to developer, administrator, coordinator roles only).
- Two-step modal: Step 1 — instruction reminder + free-text area + "Parse with AI" button. Step 2 — pre-filled editable fields (teacher, date, time, class name, studio dropdown, discipline dropdown, coverage type dropdown) plus inline clarifying question inputs from the AI response. Submit writes to `cover_requests` with `status = pending`, `source = manual`, and an `admin_notes` field recording the creating user. `writeAudit` called with `[RSO]` prefix.
- Escape key handler updated to close the new modal.
- `detectSessionInUrl` corrected from `false` to `true` (magic link login fix).

**Deploy bat:** `rso_deploy.bat` updated to copy v2 not v1 to the staging folder.

Files: `app/ritual-studio-ops-v2.html`, `migrations/2026-05-22-add-source-to-cover-requests.sql`, `docs/CHANGELOG.md`
(Edge Function deployed directly via Supabase MCP — no local file.)

---

---

## 2026-05-22 | Ritual Studio Ops | Docs update — all governance documents brought to Phase 5

DOCS_INDEX.md: updated `Last updated` to Phase 5, fixed Merger Plan v2 location (was still pointing to TM folder), corrected TM v31 status to `Legacy` (RSO Phase 4 banner added), added all Phase 2-5 RSO deliverables to section 7 (app/ritual-studio-ops-v1.html, test_phase2-5.py, reconcile.py, reconcile_reports/).

README.md: phase status table updated (Phases 0-4 Complete, Phase 5 In progress), RSO target URL updated from `*(to be created)*` to active Pages URL, directory structure updated from ritual-teacher-management31.html to ritual-studio-ops-v1.html, Merger Plan v2 location reference corrected, key contacts table updated.

LESSONS_LEARNED.md: five new lessons added (L-MG-04 through L-MG-08) covering Write tool truncation on OneDrive mounts, UTF-8 box-drawing character truncation, test string matching against variable assignments not substrings, Desktop Commander `cd /d` failure with space-containing paths, and phase-specific .bat file discipline for git commits.

Files: `docs/DOCS_INDEX.md`, `docs/README.md`, `docs/LESSONS_LEARNED.md`, `docs/CHANGELOG.md`

---

## 2026-05-22 | Ritual Studio Ops | Phase 5: Reconciliation script

New file: `scripts/reconcile.py` — daily parallel-run health check. Run once per day during the two-week Phase 5 soak period.

Checks performed on each run: (1) Audit log origin split — counts `[RSO]`-prefixed vs non-prefixed entries in the last 24h; any non-RSO entries trigger a P1 flag indicating a legacy app is still making writes. (2) Cover requests by status — reports current distribution and flags if total count drops (unexpected deletion). (3) Trainee bookings by status — flags unusual growth in pending count. (4) Teacher record count — flags any unexpected drop.

Snapshot mechanism: current state saved to `scripts/reconcile_state.json` after each run; compared against yesterday's snapshot on the next run to detect drift between runs.

Report output: plain-text report written to `scripts/reconcile_reports/YYYY-MM-DD.txt` and stdout. Exit code 0 = green, exit code 1 = P1 issue detected.

Usage: `python scripts/reconcile.py [--days N] [--no-save]`

Graceful degradation: all Supabase queries wrapped in `safe_get()`; network failures produce WARN not P1 (so the script never crashes the scheduled task).

Test suite: `scripts/test_phase5.py` — 28 checks.

Operational note: "two green weeks" and "Dashboard parity confirmation" are manual sign-off steps performed by the studio team, not automated. Run `reconcile.py --no-save` at any time for a spot-check without disturbing the snapshot.

Files: `scripts/reconcile.py`, `scripts/test_phase5.py`, `scripts/reconcile_reports/.gitkeep`

---

## 2026-05-22 | Ritual Studio Ops | Phase 4: Write-enabled shell

`WRITES_ENABLED` flipped to `true`. All TM write operations were already wired; Cover and Portal writes added.

New write operations: `approveCoverRequest(requestId)` — PATCHes `cover_requests` status to `approved`, sets `reviewed_by` / `reviewed_at`. `assignCoverRequest(requestId, className)` — prompts for notes, PATCHes status to `covered`. `acceptCoverOpportunity(candidateId, requestId)` — PATCHes `cover_candidates` response to `accepted`. `declineCoverOpportunity(candidateId, requestId)` — confirms, PATCHes to `declined`. All call `writeAudit`.

Audit origin: `writeAudit` now prefixes every description with `[RSO]` so writes from this app are distinguishable from legacy-app writes in `audit_log`.

Legacy banners added to `ritual-teacher-management31.html`, `public/cover_dashboard.html`, and `public/teacher_portal.html` — fixed bar linking to `ritual-studio-ops.pages.dev`, text: "Read-only recommended — use Ritual Studio Ops for all edits."

Version comment, build stamp, and Settings section updated to Phase 4.

Test suite: `scripts/test_phase4.py` — 24 checks (sandbox) covering WRITES_ENABLED, [RSO] prefix, write functions, onclick wiring, no hardcoded disabled buttons, legacy banners.

Files: `app/ritual-studio-ops-v1.html`, `scripts/test_phase4.py`, `Ritual_Teacher_Management/ritual-teacher-management31.html`, `Ritual_Cover_Management/public/cover_dashboard.html`, `Ritual_Cover_Management/public/teacher_portal.html`

---

## 2026-05-22 | Ritual Studio Ops | Phase 3: Cover pipeline re-pointed to RSO

All CM stage scripts (stages 1–7) copied to `services/cover/`. Original CM pipeline untouched — parallel-run safe.

New file: `services/cover/config.py` — RSO edition. Resolves `.env` from `Ritual_Studio_Ops/` root (`_RSO_ROOT = _HERE.parent.parent`). Adds `services/momence/` to `sys.path` so `MomenceAPIClient` imports without hardcoded OneDrive paths. Identical public API to CM `config.py` plus `DISCIPLINE_CODES` (canonical Phase 1 codes), `MOMENCE_DATA_DIR` (env-var backed), and `WRITES_ENABLED` default.

Hardcoded `_MOMENCE_DIR` OneDrive path hacks removed from: `stage1/momence_teacher_sync.py`, `stage3/enrich_resolved_classes_from_momence.py`, `stage6/cancellation_workflow.py`, `stage6/momence_updater.py`. Each now imports from `config`.

New feature: `--insert-new` flag in `stage1/momence_teacher_sync.py`. When set, unmatched Momence teachers are inserted to Supabase via `sb_post` rather than being silently skipped. Inserted rows carry `INITIAL_TEACHER_GRADE` and auto-generated `notes`.

`.env.template` extended with Phase 3 variables: `ANTHROPIC_API_KEY`, `NLP_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `INITIAL_TEACHER_GRADE`, `SYNC_LOOKBACK_DAYS`, `WHATSAPP_LOOKBACK_HOURS`, `NLP_CONFIDENCE_THRESHOLD`, `SMTP_*`, `CHROME_DEBUG_PORT`, `CHROME_PATH`.

Test suite: `scripts/test_phase3.py` — 65 checks covering directory structure, file existence, config.py conventions, import-hack removal, `--insert-new` flag, `.env.template` completeness, parallel-run safety.

Files: `services/cover/` (all stage files + `config.py`), `.env.template`, `scripts/test_phase3.py`

---

## 2026-05-22 | Ritual Studio Ops | Cloudflare Pages project created

`ritual-studio-ops` Pages project created via `npx wrangler pages project create ritual-studio-ops`. Production branch: `master`. Staging URL reserved: `https://ritual-studio-ops.pages.dev/`. No deployment yet — first deploy deferred to Phase 4. Wrangler version 4.82.2 used (4.93.1 available).

---

## 2026-05-22 | Ritual Studio Ops | Phase 2: Read-only merged shell

New file: `app/ritual-studio-ops-v1.html` — single-file HTML/JS merged shell.

Conventions: `sbClient`/`window.sbClient`, `onAuthStateChange`, direct REST + cached JWT, `WRITES_ENABLED = false`.

Teachers view: all six TM tabs lifted verbatim (Overview, Class History, Availability, Allocation Check, Grades ✎, Audit Trail). Five-role RBAC preserved. All TM modals and trainee flows included.

Cover view (new): Cover Requests table (reads `cover_requests` with correct column names: `class_name_raw`, `discipline_code`, `requesting_teacher_name_raw`, `coverage_type`). Teacher Portal panel (reads `cover_candidates` filtered to signed-in teacher's profile). All action buttons disabled with Phase 2 tooltip.

Schema fix: corrected cover_requests column references after live schema audit — `requesting_teacher_name_raw` not `requesting_teacher_name`; `class_name_raw` not `class_name`; `discipline_code` not `discipline`; no `cover_teacher_name` column exists.

Test suite: `scripts/test_phase2.py` — 37 checks covering conventions, tab renderers, RBAC roles, REST schema (skipped in sandboxed environments).

Files: `app/ritual-studio-ops-v1.html`, `scripts/test_phase2.py`

---

## 2026-05-21 | Ritual Studio Ops | Phase 1: Schema reconciliation

Migration: `migrations/2026-05-merged-v1.sql` applied to Supabase (rfjygyqijwgkmxboddup).

New tables (all additive, RLS on, authenticated read):
- `disciplines` — 5 rows seeded: yoga, barre, reformer, mat_pilates, yin
- `studios` — 3 rows seeded: Palm Beach (active), Robina (active), Mermaid (is_active=false)
- `momence_members` — empty Phase 7 placeholder
- `momence_bookings` — empty Phase 7 placeholder
- `momence_sync_runs` — Phase 7 sync audit log

New view:
- `teacher_directory` — id, first_name, last_name (narrow identity view, gated by teachers RLS)

Schema discoveries:
- `momence_sessions` already exists with 7,365 rows (Phase 7 session sync already running via CM)
- `anon_read_teacher_names` policy does not exist — already resolved, no action needed
- 12 CM/TM tables have RLS disabled — flagged, not auto-fixed (requires policy design per table)
- 5 tables not previously in DOCS_INDEX added: `training_courses`, `trainee_enrollments`, `timeslots`, `permissions`, `role_permissions`

DOCS_INDEX updated: tables-and-owners matrix corrected and expanded to 24 tables.

Files: `migrations/2026-05-merged-v1.sql`, `docs/DOCS_INDEX.md`

---

## 2026-05-21 | Ritual Studio Ops | Phase 0: Project skeleton created

First commit of the merged project. Folder structure, .env template, .gitignore, governance documents (DOCS_INDEX, CHANGELOG, LESSONS_LEARNED), README, services/momence stub, services/cover stub.

Files: `Ritual_Studio_Ops/` (all Phase 0 files)
Note: Momence_data code copy PENDING — MFPL OneDrive not mounted. See `services/momence/README.md`.

---

## Pre-merger changelogs (absorbed from legacy projects)

The entries below summarise the legacy project changelogs. Original files are listed in DOCS_INDEX under their respective projects and remain in place.

---

### Cover Management

#### 2026-05-20 | CM | Dashboard spinning fix
Fix for dashboard spinner that did not stop after data load.
Source: `CHANGELOG-dashboard-spinning-fix-20260520.md`

#### 2026-05-17 | CM | RLS phase 1 permissions; WhatsApp message timestamp
Applied RLS policies to permissions tables. Added `received_at` timestamp column to `whatsapp_messages`.
Migrations: `MIGRATION-rls-phase1-permissions-tables-2026-05-17.sql`, `MIGRATION-whatsapp-message-timestamp-2026-05-17.sql`

#### 2026-05-16 | CM | Phase 4 offer matching planning
Design and planning changes for offer matching (Phase 4). No schema changes.
Source: `CHANGELOG-2026-05-16.md`, `PLAN-phase4-offer-matching-2026-05-16.md`

#### 2026-05-11 | CM | Momence sessions table added
Created `momence_sessions` table in CM Supabase project. Used for Momence-side session cross-check.
Migration: `MIGRATION-momence-sessions-table-2026-05-11.sql`
Note: This table will be superseded by the Phase 1 `momence_sessions` mirror table in RSO.

#### 2026-05-09 | CM | Phase 2 dedup; permissions; Mikela merge
Deduplication of existing cover requests. Permissions migration. Mikela teacher record merge.
Migrations: `MIGRATION-phase2-dedup-2026-05-09.sql`, `MIGRATION-permissions-2026-05-09.sql`, `PHASE2-MERGE-MIKELA-2026-05-09.sql`, `PHASE2-PRE-DEDUP-FIXUPS-2026-05-09.sql`

#### 2026-05-08 | CM | Phase 1 schema hardening and resilience improvements
Extended cover request handling, improved error resilience in cover processor.
Source: `CHANGELOG-2026-05-08-phase1-and-resilience.md`

#### 2026-05-07 | CM | Scheduled task setup; class dates and resolved classes
Set up Windows Task Scheduler for monitor runs. Added class date tracking and resolved-class backfill.
Migration: `MIGRATION-class-dates-and-resolved-classes-2026-05-07.sql`
Source: `CHANGELOG-2026-05-07-scheduled-task-setup.md`

#### 2026-04-23 | CM | Availability slots
Added `avail_slots` to cover schema.
Migration: `MIGRATION-avail-slots-2026-04-23.sql`
Source: `CHANGELOG-2026-04-23-avail-slots.md`

#### 2026-04-21 | CM | Coverage type classification feature
Added `coverage_type` (temporary/permanent/both) field. NLP parser updated. Dashboard filter added.
Migration: `MIGRATION-coverage-type-2026-04-21.sql`
Sign-off: `SIGNOFF-coverage-type-2026-04-21.md`

#### 2026-04-13 | CM | NLP sender fallback
Fallback logic for sender name extraction when WhatsApp DOM heuristic fails.
Source: `CHANGELOG-2026-04-13-nlp-sender-fallback.md`

#### 2026-04-08 | CM | Stage 1 schema - initial CM schema
Created: `cover_requests`, `cover_candidates`, `cover_notifications`, `whatsapp_channels`, `whatsapp_monitor_runs`, `discipline_mappings`, `system_config`. Extended `teachers` with `whatsapp_phone` and `contact_preference`.
Migration: `stage1/01_cover_schema.sql`

---

### Teacher Management

#### 2026-04-07 | TM | Baseline restore; trainee bookings user_id
Restored to stable baseline. Added `user_id` to `trainee_bookings`.
Migration: `migrations/2026-04-07-add-trainee-bookings-user-id.sql`
Source: `CHANGELOG-2026-04-07-baseline-restore.md`

#### 2026-04-06 | TM | Course modal refinement
UI refinements to course/booking modal.
Source: `CHANGELOG-2026-04-06-course-modal-refinement.md`

#### 2026-04-05 | TM | Trainee bookings; reject flow; admin backfill; v29
Added `resolveTeacherIdForCurrentUser()`, reject modal, admin backfill UI. Fixed null-id PATCH bug. Created v29 with defensive sign-in and stray overwrite removal.
Migration: `migrations/2026-04-05-add-teacher-photo-and-momence.sql`
Source: `CHANGELOG-2026-04-05-teacher-management.md`

## 2026-06-03 | Cover Management (legacy) | Fix resolved-classes table: discipline now reads per-class Momence value (c.discipline) not request-level scalar; date cell no longer shows weekday twice | public/cover_dashboard.html

## 2026-06-07 | Cover Management (legacy) | Fix edit-modal teacher dropdown: loadTeachers() now queries anon-readable teacher_directory view (teachers table RLS blocks anon SELECT, so the list was empty and only the raw name showed); saveAndApprove() also resolves and stores requesting_teacher_id for known teachers; v1.3.29 | public/cover_dashboard.html

## 2026-06-07 | Cover Management (legacy) | Add New Request button + manual create modal to dashboard filter bar: inserts into cover_requests with source='manual', status='pending_review', synthesised raw_message (NOT NULL), resolved requesting_teacher_id; allows creating cover requests when a teacher never posts in WhatsApp; v1.3.30 | public/cover_dashboard.html

## 2026-06-07 | RSO merged app (v2) | Fix New Manual Cover Request submit (was failing silently: insert omitted NOT NULL raw_message): now synthesises raw_message, sets status='pending_review' (was 'pending', matching neither app's workflow), confidence_score=1, message_timestamp | app/ritual-studio-ops-v2.html

## 2026-06-07 | Cover Management (legacy) | New Request modal now offers free-form entry: paste/type the message, Parse with AI (parse-cover-request edge function, called with anon key) pre-fills the structured fields and surfaces clarifying questions; pasted message stored as raw_message; v1.3.31 | public/cover_dashboard.html
2026-06-08 | Teacher Management (Trainee Bookings) | Fixed booking not persisting: captured pendingBookingPayload before closeConfirmBookingModal() nulled it; added user_id (auth UID) to booking row | Ritual_Studio_Ops/app/ritual-studio-ops-v2.html
  
2026-06-09 | Cover Management (backend) | Fixed IndentationError in cover_processor.py caused by 3 duplicate trailing lines introduced in commit 03a86aa (2026-06-08 21:48). Crashed all June 9 morning monitor runs silently; Leah's 20:28 cover request missed until 2pm run. | stage2/cover_processor.py (commit bb23ecd) 
2026-06-15 | Teacher Management (Trainee Bookings) | Fixed wrong teacher assigned to booking: guarded fuzzy email match in resolveTeacherIdForCurrentUser to skip null/empty emails | Ritual_Studio_Ops/app/ritual-studio-ops-v2.html
