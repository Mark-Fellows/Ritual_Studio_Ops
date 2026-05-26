# Portal Developer Reference — `app/index.html`

Frontend-specific notes for the Ritual Management Portal served from
`Ritual_Studio_Ops/app/`. For backend details see the main `docs/` files.

---

## Tile permission system

### How it works

After sign-in, `showAuthed(profile, perms)` runs. It:

1. Builds a `Set` from the `perms` array (fetched from `v_role_permissions_resolved`
   filtered to the signed-in user's role).
2. Selects **every element** with a `[data-perm]` attribute.
3. For each element, checks whether the `data-perm` value is in the set:
   - **Present** → tile remains interactive.
   - **Absent** → `.disabled` class added: `opacity: 0.45`, `filter: grayscale(0.6)`,
     `cursor: not-allowed`, `pointer-events: none`.

Elements **without** `data-perm` are never touched and remain active for all users.

---

### Adding a new gated tile

Only add `data-perm` if you want to restrict access by role. Before adding it,
verify the permission code exists in the database:

```sql
SELECT DISTINCT permission_code
FROM v_role_permissions_resolved
ORDER BY permission_code;
```

If the code is missing from the view, **every user will see the tile greyed out**,
regardless of their role.

To add a new permission:
1. Insert into `role_permissions` (or the relevant seed table).
2. Confirm the code appears in `v_role_permissions_resolved` for the target role.
3. Then add `data-perm="your.new.code"` to the tile.

---

### The Ritual Campaigns tile — special case

**The Ritual Campaigns tile (`id="campaign-tile"`) must NOT have a `data-perm`
attribute.**

Reason: `index.tile.ritual_campaigns` does not exist in `v_role_permissions_resolved`.
Adding `data-perm` with this code greys the tile for every user. The campaign app
(`ritual-campaign-planning.pages.dev`) has its own Supabase auth — no portal gate
is needed. A protective HTML comment in `app/index.html` repeats this warning.

---

## Cache headers (`app/_headers`)

All HTML files must be served with `Cache-Control: no-cache, no-store, must-revalidate`
to prevent browsers or Cloudflare's CDN from serving a stale version after deployment.

If you add a new HTML page, add a matching rule to `app/_headers`:

```
/your-page.html
  X-Frame-Options: SAMEORIGIN
  X-Content-Type-Options: nosniff
  Cache-Control: no-cache, no-store, must-revalidate
```

---

## Deployment

The portal is a Cloudflare Pages project that auto-deploys from
`Mark-Fellows/ritual-studio-ops` (or equivalent) on push to `main`.
The `app/` directory is the deployment root.

---

## Known issues / history

| Date       | Issue | Fix | Notes |
|------------|-------|-----|-------|
| 2026-05-26 | Campaigns tile greyed — `data-perm` code absent from DB view; no cache headers | Removed `data-perm`; added `app/_headers` with no-cache; added protective HTML comment | See `docs/CHANGELOG-2026-05-26-portal-campaign-tile.md` |
