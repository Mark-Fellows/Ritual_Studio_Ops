// _middleware.js  —  redirects the pages.dev URL to the canonical custom domain
// for the ops Pages project.
//
// Redirects any *.pages.dev request to the custom domain so the app is only ever
// reached at one canonical URL (consistent caching/headers, no split traffic).
// It ONLY acts when the host ends in ".pages.dev"; every other host (the custom
// domain, etc.) passes through unchanged, so it cannot break the staff-facing site.
// Any error also falls through to next().
//
// NOTE (2026-07-24): originally added to stop the pages.dev URL bypassing
// Cloudflare Access. Access has since been removed from this app — "Ritual Ops —
// staff" was switched from the "Ritual Studio Staff" Allow policy to "Open – no
// auth (Bypass)" in Cloudflare Zero Trust, since the portal's own Supabase
// user_profiles/RBAC check (Settings > User Management) already fully gates the
// authenticated app. "Ritual Cover - staff" still uses the Allow policy and was
// left untouched. The canonical-domain redirect below is unrelated to that and is
// still worth keeping. See docs/CHANGELOG.md, 2026-07-24.
//
// Using 302 (temporary) so nothing is cached while you verify. Switch to 301 later.

const CUSTOM_DOMAIN = "ritual-ops.lesss.com.au"; // ops project

export async function onRequest(context) {
  try {
    const { request, next } = context;
    const url = new URL(request.url);
    if (url.hostname.toLowerCase().endsWith(".pages.dev")) {
      url.hostname = CUSTOM_DOMAIN; // preserves path, query string and hash
      return Response.redirect(url.toString(), 302);
    }
    return next();
  } catch (e) {
    return context.next();
  }
}
