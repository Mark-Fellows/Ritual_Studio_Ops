# CHANGELOG — 2026-05-26 — Portal: Campaign tile greyed-out fix

## Symptom
The Ritual Campaigns tile on the Management Portal appeared greyed out
(reduced opacity, grayscale, `cursor: not-allowed`) after a deployment.
Clicking the tile had no effect.

## Root cause (primary) — stale cache
The portal's `app/_headers` file did not exist, so no `Cache-Control` directive
was in place for `index.html`. Without it, Cloudflare's CDN or the browser
may serve a stale copy of the page — one where the `data-perm` attribute
had been re-introduced — causing the tile to be disabled again.

## Root cause (secondary) — incorrect `data-perm` attribute
The portal's permission check (`showAuthed`) iterates over every element with a
`[data-perm]` attribute and toggles the `.card.disabled` CSS class based on
whether the code appears in `v_role_permissions_resolved` for the signed-in
user's role.

The permission code `index.tile.ritual_campaigns` does **not** exist in that view
(the campaign app has its own Supabase auth and needs no portal-level gate).
Any tile whose `data-perm` code is absent from the view is automatically disabled
for **all** users.

## Fix applied

### 1. `app/index.html` — removed `data-perm` from Campaigns tile
Removed `data-perm="index.tile.ritual_campaigns"` and added a warning HTML
comment so future editors see the explanation before making changes.

### 2. `app/_headers` — new file, adds `Cache-Control: no-cache` for HTML
Prevents Cloudflare or browsers from serving a stale version of `index.html`
after any deployment.

## Prevention
- **Never add `data-perm` to the Campaigns tile** unless you first add the
  matching permission code to `v_role_permissions_resolved` (or a seeded row
  in `role_permissions`). Verify first:
  ```sql
  SELECT DISTINCT permission_code FROM v_role_permissions_resolved ORDER BY 1;
  ```
- For any new gated tile, confirm the code exists in the view before adding
  `data-perm`. If absent, all users see the tile disabled.
- The `_headers` file now ensures fresh HTML is always served after deployment.

## Files changed
- `app/index.html` — removed `data-perm`; added protective comment
- `app/_headers` — new file
- `docs/PORTAL-DEVELOPER.md` — new portal frontend reference doc
- `docs/CHANGELOG-2026-05-26-portal-campaign-tile.md` — this file
