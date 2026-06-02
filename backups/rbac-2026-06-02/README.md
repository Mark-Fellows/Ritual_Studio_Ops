# Backup — RBAC unification (2026-06-02)

Pre-change backup taken before applying the RBAC unification (User Admin Phase 5.0/5.1/5.2)
to the shared Supabase project `rfjygyqijwgkmxboddup` and the merged app.

## Contents

- `GIT-HEADS.txt` — git HEAD + branch for both repos at backup time.
- `db_snapshot.json` — permissions catalogue, role_permissions grants, user_profiles
  roles, the pre-change `user_profiles` RLS policies, and the `v_role_permissions_resolved`
  / `get_my_role()` definitions.
- `ROLLBACK.sql` — undoes the additive unification and restores the original
  developer-only `user_profiles` write policies. Apply via Supabase MCP only if needed.
- `app/ritual-studio-ops-v2.html.pre` — pre-change copy of the merged app (≈289 KB).
- `app/index.html.pre` — pre-change copy of the portal launcher.

## Restore

- **DB:** apply `ROLLBACK.sql`. Then re-verify `SELECT count(*) FROM permissions;` = 26.
- **App files:** copy the `.pre` files back over `app/ritual-studio-ops-v2.html` and
  `app/index.html`, or `git checkout` the recorded HEADs.

## Notes

- The merged app file is large and the Edit/Write tools have truncated it before
  (L-MG-19/20). All edits to it in this work were done with deterministic Python patchers
  verified by `node --check` + byte-count + closing-`</html>` checks.
- No production deploy (no git push) was performed during the autonomous session; the DB
  migrations are additive and the live app keeps reading the old view until the JS is
  deployed.

## Update (2026-06-03)

- `app/index.html` was found TRUNCATED in the working tree (82,552 bytes, unclosed
  `<script>`) — a pre-existing corruption (L-MG-21). The `.pre` copy here captured that
  truncated state, so DO NOT restore index.html from `.pre`. The intact source is git HEAD
  (87,441 bytes); it was restored via `git show HEAD:app/index.html` and then the 5.1 view
  swap applied. Current working `app/index.html` is the good, patched version.
- DB migrations applied this session: rbac_unification_backbone_2026_06_02,
  user_admin_rpcs_and_rls_2026_06_02, user_admin_harden_grants_2026_06_02. Use ROLLBACK.sql
  to revert all three.
- App changes staged but NOT committed/pushed (sandbox cannot write .git/index.lock).
