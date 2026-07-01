// _middleware.js  —  closes the pages.dev "back door" for the ops Pages project.
//
// Redirects any *.pages.dev request to the protected custom domain so Cloudflare
// Access cannot be bypassed. It ONLY acts when the host ends in ".pages.dev";
// every other host (your custom domain, etc.) passes through unchanged, so it
// cannot break the staff-facing site. Any error also falls through to next().
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
