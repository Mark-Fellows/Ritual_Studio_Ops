# Ritual Studio Timetable — Working Memory

> Claude reads this file at the start of every session. Keep it current.
> Last updated: 2026-06-12

---

## Project Identity

| Item | Value |
|------|-------|
| **Project** | Ritual Studio Timetable |
| **Status** | Live — "Still in use — not yet merged" per SOURCE_OF_TRUTH.md |
| **HTML output file** | `Ritual_Cover_Management\public\studio_timetable.html` |
| **Python generator** | `Ritual_Studio_Ops\services\cover\tools\generate_timetable_html.py` |
| **Timetable template** | `Ritual_Studio_Ops\services\cover\tools\timetable_template.html` |
| **Production URL** | `https://ritual-cover-management.pages.dev/studio_timetable.html` |
| **Cloudflare Pages project** | `ritual-cover-management` (build output: `public/`) |
| **Supabase project** | `rfjygyqijwgkmxboddup` — shared by ALL FOUR Ritual apps; schema changes are immediately live everywhere |

---

## ⚠ Three Rules That Cause Silent Failures

1. **Run git from inside the correct repo folder**, never from the `Ritual_Apps` parent. This project spans two repos — confirm which files changed and commit to each repo separately (see Git instructions below).
2. **`Ritual_Teacher_Management` is a LEGACY duplicate** on a different URL. The production portal is `Ritual_Studio_Ops/app/index.html`. The Timetable is unrelated to that portal.
3. After pushing, confirm a **Production** build ran for your commit in the Cloudflare **Deployments** tab, then hard-refresh the live URL.

---

## Two Components — Confirm Which Is Affected Before Editing

The timetable has two distinct components that must not be confused:

| Component | File | Repo |
|-----------|------|------|
| **HTML output** (what users see) | `Ritual_Cover_Management\public\studio_timetable.html` | `ritual-cover-management` (branch: `main`) |
| **Python generator** (produces the HTML) | `Ritual_Studio_Ops\services\cover\tools\generate_timetable_html.py` | `Ritual_Studio_Ops` (branch: `master`) |
| **HTML template** (used by the generator) | `Ritual_Studio_Ops\services\cover\tools\timetable_template.html` | `Ritual_Studio_Ops` (branch: `master`) |

**The generator lives in the RSO project, not in `Ritual_Cover_Management`.** Do not look for a generator inside `Ritual_Cover_Management` — there is none. The generator writes its output to `Ritual_Cover_Management\public\studio_timetable.html` for deployment.

**Decision rule:**
- Visual/CSS/JS fix only → edit `studio_timetable.html` directly
- Logic, data, or structural change → edit the generator and/or template in RSO, then regenerate
- Both → edit generator first, regenerate, review output, then deploy

---

## Required Reading — Before Any Edit

Read in this order before making changes:

1. `Ritual_Studio_Ops\docs\SOURCE_OF_TRUTH.md` — confirms this screen is still live and not yet merged; notes which file backs it
2. `Ritual_Studio_Ops\docs\LESSONS_LEARNED.md` — hard-won constraints across all four Ritual apps; read in full
3. `Ritual_Cover_Management\ARCHITECTURE.md` — how the timetable fits into the Cover Management pipeline; relationship between generator and HTML output
4. `Ritual_Cover_Management\DEVELOPER.md` — developer conventions; deployment notes
5. `Ritual_Studio_Ops\docs\CHANGELOG.md` — review the last five entries for any recent timetable or pipeline changes

---

## Files — Allowed Modifications

| File | Condition |
|------|-----------|
| `Ritual_Cover_Management\public\studio_timetable.html` | Visual/CSS/JS change only, or after regeneration |
| `Ritual_Studio_Ops\services\cover\tools\generate_timetable_html.py` | Generation logic change |
| `Ritual_Studio_Ops\services\cover\tools\timetable_template.html` | Template/structure change |
| `Ritual_Studio_Ops\migrations\YYYY-MM-DD-[description].sql` | Schema change only; **do not apply until Mark confirms** |

## Files — Must NOT Be Modified

| File | Reason |
|------|--------|
| `public\cover_dashboard.html` | Separate screen; out of scope |
| `public\teacher_portal.html` | Separate screen; out of scope |
| `public\index.html` | Cover Management launcher; out of scope |
| `services\cover\tools\generate_timetable_html.py.bak-2026-05-11` | Backup file — do not touch |
| Any file under `Ritual_Teacher_Management\` | Separate project |
| `.env` | Never commit credentials |

---

## Regeneration Step (Required When Generator Is Changed)

If `generate_timetable_html.py` or `timetable_template.html` was modified:

1. Run `regenerate_timetable.bat` (or the equivalent Python command) from inside `Ritual_Studio_Ops\services\cover\tools\`
2. Confirm the output written to `Ritual_Cover_Management\public\studio_timetable.html` looks correct
3. Get Mark's approval on the HTML output before deploying
4. Then proceed to deployment

Do not deploy the old `studio_timetable.html` after changing the generator without regenerating first.

---

## Supabase MCP Instructions

- Use `execute_sql` for read-only investigation — inspect live data before writing queries
- Use `apply_migration` **only after Mark has reviewed and approved the SQL**
- Always state the shared-database risk explicitly before applying anything (affects all four Ritual apps simultaneously)
- Verify after applying with a `SELECT` confirming the change landed correctly

---

## Cloudflare MCP Instructions

| Item | Value |
|------|-------|
| Account | `db7b2002741f559dc7d8558afc1abf07` (Staff@ritualpalmbeach.com) |
| Pages project | `ritual-cover-management` |
| Build output | `public/` |
| Production URL | `https://ritual-cover-management.pages.dev` |

- If `studio_timetable.html` was changed directly → deploy `public/` to `ritual-cover-management`
- If the Python generator was changed → **regenerate first**, review output, then deploy
- Do **not** deploy until Mark confirms the output is correct
- Confirm deployment URL and build ID after deploy

---

## Git / Commit Instructions

This project spans two repos. Commit to the correct repo for each file changed. A single task may require commits to both.

**For changes to `public\studio_timetable.html`:**
- Remote: `https://github.com/Mark-Fellows/ritual-cover-management.git`
- Branch: `main` (repo also has a `cloudflare` branch — confirm the Pages production branch before relying on auto-deploy)
- Commit format: `[Timetable] Short description — html output`

**For changes to `generate_timetable_html.py` or `timetable_template.html`:**
- Remote: `https://github.com/Mark-Fellows/Ritual_Studio_Ops.git`
- Branch: `master`
- Commit format: `[Timetable] Short description — generator`

In both cases:
1. Run `git remote -v` and `git status -sb` to confirm remote and branch before committing
2. Stage only files modified for this change
3. Commit with the appropriate format above
4. Confirm push succeeded and show commit hash

---

## Post-Change Documentation (Mandatory)

1. Append one entry to `Ritual_Studio_Ops\docs\CHANGELOG.md`:
   `YYYY-MM-DD | Studio Timetable | [summary] | [files changed]`
2. If a new technical constraint is discovered, append to `Ritual_Studio_Ops\docs\LESSONS_LEARNED.md`

---

## Definition of Done

- [ ] `SOURCE_OF_TRUTH.md` confirmed — correct component(s) identified (HTML output, generator, or both)
- [ ] Only the files listed above modified
- [ ] Local change reviewed and approved by Mark
- [ ] Timetable regenerated via `regenerate_timetable.bat` and HTML output reviewed (if generator was changed)
- [ ] Schema migration reviewed, approved, applied, and verified via Supabase MCP (if applicable)
- [ ] Deployed to `ritual-cover-management.pages.dev` and confirmed live
- [ ] Committed and pushed to the correct GitHub repo(s) with correct commit formats
- [ ] `CHANGELOG.md` entry added to the RSO master changelog

---

## Key File Locations

| Document | Path |
|----------|------|
| HTML output (deployed) | `Ritual_Cover_Management\public\studio_timetable.html` |
| Python generator | `Ritual_Studio_Ops\services\cover\tools\generate_timetable_html.py` |
| HTML template | `Ritual_Studio_Ops\services\cover\tools\timetable_template.html` |
| Generator backup | `Ritual_Studio_Ops\services\cover\tools\generate_timetable_html.py.bak-2026-05-11` |
| Architecture doc | `Ritual_Cover_Management\ARCHITECTURE.md` |
| Developer conventions | `Ritual_Cover_Management\DEVELOPER.md` |
| Source of truth | `Ritual_Studio_Ops\docs\SOURCE_OF_TRUTH.md` |
| Lessons learned | `Ritual_Studio_Ops\docs\LESSONS_LEARNED.md` |
| Master changelog | `Ritual_Studio_Ops\docs\CHANGELOG.md` |
| Deployment map | `Ritual_Apps\RSO_DEPLOYMENT_MAP.md` (Ritual_Apps root) |
