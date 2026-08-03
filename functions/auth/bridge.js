// bridge.js — Cloudflare Access → Supabase session bridge (A3 spike)
// ============================================================================
// DEPLOY LOCATION (Cover project): functions/auth/bridge.js  → route /auth/bridge
//
// What it does
// ------------
// Cloudflare Access attaches a signed JWT to every request it lets through
// (header "Cf-Access-Jwt-Assertion"). This function:
//   1. verifies that JWT (signature via the team JWKS, plus audience + issuer + expiry),
//   2. reads the user's email FROM THE VERIFIED TOKEN (never from the client),
//   3. asks Supabase (Admin API, secret key) for a one-time magic-link token for
//      that email — WITHOUT sending an email,
//   4. returns { email, token_hash } as JSON.
// The browser then calls supabase.auth.verifyOtp({ token_hash, type: 'email' })
// to establish a real Supabase session. No password, no emailed link.
//
// Security model
// --------------
// * Only a request that passed Cloudflare Access carries a valid JWT, so only
//   signed-in @ritualpalmbeach.com staff can obtain a token_hash.
// * The email is taken from the cryptographically verified JWT, so a caller
//   cannot mint a session for anyone else.
// * The Supabase SECRET key lives only here (a Pages env var), never in the browser.
// * token_hash is single-use and short-lived.
//
// Required Pages environment variables (set in Cloudflare, see README):
//   SUPABASE_URL           e.g. https://rfjygyqijwgkmxboddup.supabase.co
//   SUPABASE_SERVICE_KEY   the sb_secret_… key  (SECRET — mark as encrypted)
//   CF_ACCESS_TEAM_DOMAIN  https://ritualyogaandpilates.cloudflareaccess.com
//   CF_ACCESS_AUD          the Cover application's Audience (AUD) tag
// ----------------------------------------------------------------------------

const JWKS_TTL_MS = 5 * 60 * 1000; // cache the team public keys for 5 minutes
let _jwks = { at: 0, keys: null };

function b64urlToBytes(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function b64urlToJson(s) {
  return JSON.parse(new TextDecoder().decode(b64urlToBytes(s)));
}

async function getKeys(teamDomain) {
  if (_jwks.keys && Date.now() - _jwks.at < JWKS_TTL_MS) return _jwks.keys;
  const res = await fetch(`${teamDomain}/cdn-cgi/access/certs`);
  if (!res.ok) throw new Error("jwks fetch failed");
  const json = await res.json();
  _jwks = { at: Date.now(), keys: json.keys || [] };
  return _jwks.keys;
}

// Verify a Cloudflare Access JWT (RS256) with the Web Crypto API — no deps.
async function verifyAccessJwt(token, teamDomain, expectedAud) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("malformed token");
  const [h, p, sig] = parts;
  const header = b64urlToJson(h);
  const payload = b64urlToJson(p);

  const keys = await getKeys(teamDomain);
  const jwk = keys.find((k) => k.kid === header.kid);
  if (!jwk) throw new Error("signing key not found");

  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"]
  );
  const ok = await crypto.subtle.verify(
    { name: "RSASSA-PKCS1-v1_5" },
    key,
    b64urlToBytes(sig),
    new TextEncoder().encode(`${h}.${p}`)
  );
  if (!ok) throw new Error("bad signature");

  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) throw new Error("token expired");
  if (payload.nbf && payload.nbf > now + 60) throw new Error("token not yet valid");
  if (payload.iss && payload.iss !== teamDomain) throw new Error("issuer mismatch");
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (expectedAud && !auds.includes(expectedAud)) throw new Error("audience mismatch");
  if (!payload.email) throw new Error("no email in token");
  return payload;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

export async function onRequest(context) {
  const { request, env } = context;

  const TEAM = env.CF_ACCESS_TEAM_DOMAIN;
  const AUD = env.CF_ACCESS_AUD;
  const SB_URL = env.SUPABASE_URL;
  const SB_KEY = env.SUPABASE_SERVICE_KEY;
  if (!TEAM || !AUD || !SB_URL || !SB_KEY) {
    return json({ error: "bridge not configured" }, 500);
  }

  // Cloudflare Access attaches the assertion header on every authenticated request.
  const token =
    request.headers.get("Cf-Access-Jwt-Assertion") ||
    request.headers.get("cf-access-jwt-assertion");
  if (!token) return json({ error: "no access token (not behind Access?)" }, 401);

  let claims;
  try {
    claims = await verifyAccessJwt(token, TEAM, AUD);
  } catch (e) {
    return json({ error: "access token invalid" }, 401);
  }

  // Mint a one-time magic-link token for the verified email (no email is sent).
  let gen;
  try {
    const r = await fetch(`${SB_URL}/auth/v1/admin/generate_link`, {
      method: "POST",
      headers: {
        apikey: SB_KEY,
        Authorization: `Bearer ${SB_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ type: "magiclink", email: claims.email }),
    });
    gen = await r.json();
    if (!r.ok) throw new Error(gen && gen.msg ? gen.msg : "generate_link failed");
  } catch (e) {
    return json({ error: "could not mint session" }, 502);
  }

  // GoTrue returns the hashed one-time token as `hashed_token`.
  const token_hash = gen.hashed_token || (gen.properties && gen.properties.hashed_token);
  if (!token_hash) return json({ error: "no token issued" }, 502);

  return json({ email: claims.email, token_hash });
}
