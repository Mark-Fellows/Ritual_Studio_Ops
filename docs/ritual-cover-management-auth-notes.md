# Ritual Cover Management Portal — Auth Fix Notes

**Project:** `ritual-cover-management.pages.dev`  
**Date resolved:** May 2026  
**Status:** Fixed and deployed

---

## The Problem

Users had to request a new Magic Link every single time they visited the portal. Sessions were not persisting between visits. The URL after clicking the link contained an OTP-expired error:

```
https://ritual-cover-management.pages.dev/?error=access_denied&error_code=otp_expired
```

Despite this error, the user was still briefly authenticated via a stale session already in `localStorage` — masking the true cause.

---

## Root Cause 1 — Implicit Auth Flow

The Supabase client was configured with `flowType: 'implicit'`:

```javascript
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: {
    flowType: 'implicit',   // ← this was the problem
    ...
  }
});
```

With implicit flow, the access token and refresh token are embedded in the URL hash (`#access_token=...`). Supabase has a security setting — **"Detect and revoke potentially compromised refresh tokens"** — enabled on this project. This setting treats any token that appears in a URL as potentially compromised and revokes it immediately. Result: every login produced a refresh token that was revoked on arrival, forcing a new Magic Link every time.

**Fix:** Changed `flowType` from `'implicit'` to `'pkce'` in `public/index.html`.

With PKCE (Proof Key for Code Exchange):
- The browser generates a secret *code verifier* stored in `localStorage`
- A hashed *code challenge* is sent to Supabase when the Magic Link is requested
- The email link contains a `?code=` parameter (not tokens in the hash)
- The browser exchanges the code for tokens server-side — tokens never appear in the URL
- Refresh tokens survive and sessions persist correctly

---

## Root Cause 2 — SIGNED_IN Event Blocking INITIAL_SESSION

After switching to PKCE, the Magic Link now produced a `?code=` URL and `SIGNED_IN` fired correctly in the console — but the dashboard never appeared.

### How Supabase JS fires auth events (critical insight)

Supabase JS **serialises** `onAuthStateChange` events. It does not fire the next event until the current event's async handler has fully resolved.

With PKCE, the event sequence when a magic link is clicked is:

1. `INITIAL_SESSION` (null) — fires before the code exchange completes
2. `SIGNED_IN` — fires immediately when the PKCE token exchange succeeds
3. `INITIAL_SESSION` (valid session) — fires **after** the `SIGNED_IN` handler resolves

The original code handled `SIGNED_IN` by calling `loadProfileAndPerms()`, which makes two REST calls to Supabase (to `user_profiles` and `v_role_permissions_resolved`). These calls **hang indefinitely** when triggered from the `SIGNED_IN` handler, because the Supabase JS client is not ready to make authenticated REST calls at that exact moment in the PKCE exchange.

Because the `SIGNED_IN` handler never resolved, Supabase never fired `INITIAL_SESSION` (step 3 above). The portal was permanently stuck on the login screen.

### How it was confirmed

A 10-second timeout was temporarily added to the REST call. This forced the `SIGNED_IN` handler to complete (with an error), which unblocked `INITIAL_SESSION`. The second attempt — from `INITIAL_SESSION` — succeeded immediately because the session was fully settled in `localStorage` by then.

Debug output that confirmed the sequence:

```
10:27:59  state change: SIGNED_IN staff@ritualpalmbeach.com
10:27:59  handleSession _authHandled=false hasSession=true
10:27:59  loadProfileAndPerms start uid=e8953d96-...
10:28:09  handleSession ERROR: TIMEOUT: user_profiles query took >10s
10:28:09  state change: INITIAL_SESSION staff@ritualpalmbeach.com   ← fired the instant SIGNED_IN handler returned
10:28:09  handleSession _authHandled=false hasSession=true
10:28:09  loadProfileAndPerms start uid=e8953d96-...
10:28:11  user_profiles: OK role=developer
10:28:11  permissions: OK count=26
10:28:11  showAuthed complete — overlay should be hidden now         ← portal loaded!
```

**Fix:** Stop handling `SIGNED_IN` in `onAuthStateChange`. Return immediately from that branch so `INITIAL_SESSION` fires without delay:

```javascript
sb.auth.onAuthStateChange(async (event, session) => {
  if (event === 'INITIAL_SESSION' || event === 'TOKEN_REFRESHED') {
    await handleSession(session);
  } else if (event === 'SIGNED_IN') {
    // Intentional no-op.
    // With PKCE, the client is not ready for REST calls when SIGNED_IN fires.
    // Returning immediately allows INITIAL_SESSION to fire next, at which
    // point the session is fully settled and REST calls work correctly.
  } else if (event === 'SIGNED_OUT') {
    _authHandled = false;
    showLogin();
  }
});
```

---

## Files Changed

### `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\public\index.html`

| What changed | Where |
|---|---|
| `flowType: 'implicit'` → `flowType: 'pkce'` | Supabase `createClient` call (~line 621) |
| `onAuthStateChange` — removed `SIGNED_IN` from handled events | Auth flow section (~line 828) |
| Added `SIGNED_IN` no-op branch with explanatory comment | Same block |

The file is deployed via **Cloudflare Pages**, connected to the GitHub repository **`Mark-Fellows/ritual-cover-management`** (private, `main` branch). Any push to `main` triggers an automatic redeploy.

---

## Infrastructure

| Component | Detail |
|---|---|
| Frontend | Cloudflare Pages — `ritual-cover-management.pages.dev` |
| GitHub repo | `Mark-Fellows/ritual-cover-management` (private, branch: `main`) |
| Local path | `C:\Users\markj\OneDrive\Desktop\Ritual_Apps\Ritual_Cover_Management\` |
| Backend | Supabase project ID `rfjygyqijwgkmxboddup` |
| Auth method | Magic Link (OTP) with PKCE flow |
| Supabase plan | Pro |

### Key Supabase settings (do not change)
- **"Detect and revoke potentially compromised refresh tokens"** — ON. This is why PKCE is required. Switching back to implicit flow will break sessions again.
- **Site URL:** `https://ritual-cover-management.pages.dev`
- **Redirect URLs:** `https://ritual-cover-management.pages.dev/**`

### Database — relevant tables and policies

**`user_profiles`** (RLS enabled)
- `Users can read own profile` — `auth.uid() = user_id` — allows any authenticated user to read their own row
- `Developers and admins can read all profiles` — uses `get_my_role()` function (SECURITY DEFINER, safe)

**`permissions`** and **`role_permissions`** (RLS enabled)
- Both have a single policy: `qual: true` for the `authenticated` role — any logged-in user can read them
- These are queried via the view `v_role_permissions_resolved` to build the user's permission set

**`get_my_role()` function** — SECURITY DEFINER, queries `user_profiles` bypassing RLS. Used within RLS policies — safe, no recursion.

---

## How the Auth Flow Now Works

1. User visits the portal → `INITIAL_SESSION` fires with existing localStorage session → dashboard loads (no login needed)
2. Session expired or first visit → `INITIAL_SESSION` fires with null → login form shown
3. User enters email → Magic Link sent → PKCE code verifier stored in browser's `localStorage`
4. User pastes the `?code=` link into the **same browser window** (important — different windows/incognito will fail because the verifier won't be there)
5. `SIGNED_IN` fires → our handler returns immediately (no-op)
6. `INITIAL_SESSION` fires with fully settled session → `loadProfileAndPerms()` → `showAuthed()` → dashboard

---

## Known Gotchas

- **Do not open the magic link in a different browser or incognito window** from the one used to request it. The PKCE verifier is stored in that window's `localStorage`. A different context has no verifier, the code exchange silently fails, and the portal stays on the login screen.
- **OTP rate limiting:** Supabase limits the number of Magic Link emails per hour. If no email arrives, check spam and wait 5–10 minutes before requesting another.
- **OTP expiry:** Magic links expire. Click them promptly (within a few minutes). Multiple clicks on the same link will fail after the first use ("One-time token not found").
- The `cover_dashboard.html` admin page intentionally uses `persistSession: false` — it does not share the session with `index.html` and requires its own authentication. This is by design.
