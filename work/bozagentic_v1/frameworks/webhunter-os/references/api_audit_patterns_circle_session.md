# API Audit Patterns — Session-Derived Reference (Circle Sandbox, 2026-07)

Patterns and pitfalls from an unauthenticated audit of `app-sandbox.circle.com` (Circle Mint, a Next.js SPA) and `api-sandbox.circle.com` (REST + Apollo Server GraphQL). The site is gated by a Cloudflare "Lockout" bot challenge, so the entire audit runs on the unauthenticated surface: the 401-walled REST API, the field-validation-erroring GraphQL endpoint, and the public Next.js static asset tree. Each pattern is reproducible and applicable to any Next.js + Apollo Server stack behind a Cloudflare WAF.

## 1. 401/404 Differential for REST Endpoint Enumeration (High — prerequisite for everything else)

**Symptom:** A black-box REST API returns `401 Unauthorized` for some paths and `404 Not Found` for others. The 401s are real endpoints behind an auth wall; the 404s are decorative.

**Detection recipe:**
```bash
# Sweep candidate paths, expect 401 = exists, 404 = doesn't exist
for p in /v1/payments /v1/transfers /v1/wallets /v1/balances /v1/cards \
         /v1/payouts /v1/settlements /v1/configuration; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' https://target$p)  $p"
done
```

**Result on Circle:** `/v1/payments`, `/v1/transfers`, `/v1/wallets`, `/v1/accounts`, `/v1/balances`, `/v1/cards`, `/v1/payouts`, `/v1/configuration` all returned 401. `/v1/business-accounts`, `/v1/notifications`, `/v1/users`, `/v1/sessions`, etc. returned 404.

**Bonus differential:** On the same API, `/v1/balances/1` returned 404 while `/v1/payments/1` returned 401. This tells you which endpoints accept per-resource sub-paths (`/payments/{id}`) and which are collection-only (`/balances`).

**Why it works:** Most auth frameworks run an auth check *before* the routing check, so any path that hits a real route returns 401 regardless of whether the resource exists, while unknown paths skip straight to a 404. This is the highest-yield recon move for any walled REST API.

## 2. Verbose Error Messages Leak API Key Format and Internal Constraints (High)

**Symptom:** When the API receives a malformed bearer token, instead of a generic "invalid token" it returns the full format spec, including example values.

**Detection recipe:**
```bash
curl -s -H "Authorization: Bearer fake:key" "https://target/v1/anything" | head -c 500
```

**Real transcript on Circle:**
```
{"code":401,"message":"malformed API key. API key should contain three substrings,
 separated by a colon. First substring denotes the environment, e.g. TEST_API_KEY.
 Second substring denotes the ID of the key, e.g. ebb3ad72232624921abc4b162148bb84.
 Third substring denotes the secret of the key, e.g. 019ef3358ef9cd6d08fc32csfe89a68d.
 This format only applies to API keys generated after May 2023"}
```

**What to look for in similar verbose errors:**
- Example values (test if they are *real* or just documentation — usually docs)
- The exact structural spec (separator, lengths, charset, version constraints)
- The fact that format-vs-credential errors are distinct strings enables a small brute-force / format oracle

**Report framing:** "Verbose error message reveals the internal API key format. The error includes example values, separator rules, and version info ('API keys generated after May 2023'), which aids offline attacks and gives attackers a complete blueprint for credential stuffing." CWE-209.

**Format oracle trick:** Try keys with valid format but wrong secrets → server returns "Invalid credentials." Try keys with wrong format → server returns the verbose format error. This is a binary oracle. In some auth systems, this enables timing-based key-recovery on weak secrets if the validation order short-circuits the format check first. (Not exploitable on Circle; both 401 paths returned in similar time. Worth checking on every walled API.)

## 3. GraphQL Field-Probing Bypasses "Introspection Disabled" (High)

**Symptom:** Apollo Server with `introspection: false` blocks `__schema`/`__type` queries, but per-field validation errors on the Query type still leak the full schema.

**Detection recipe:**
```bash
# Apollo's introspection guard blocks __schema but NOT individual fields.
# Brute force field names; any field that doesn't return "Cannot query field"
# exists. Same trick for nested type fields and for arg names.
for field in user me viewer session config featureFlags version; do
  curl -s -X POST https://target/api/graphql \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{$field}\"}"
done

# Discover arguments on a query by trying common arg names
for arg in id userId uuid email "userId:\"1\""; do
  curl -s -X POST https://target/api/graphql \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{user($arg){id}}\"}"
done

# Discover required input fields on a mutation by passing {} and reading the error
curl -s -X POST https://target/api/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation{createAccount(input:{}){__typename}}"}'
# Error: "Field \"CreateAccountInput.firstName\" of required type \"String!\" was not provided."
# ... repeat-enumerate all required args from the multi-error response
```

**What this gives you:**
- Every query and mutation name on the `Query`/`Mutation` type
- Every field on every reachable type (try nested selections)
- Every argument on every query/mutation/field
- Required vs optional input fields (required ones appear in `{}` errors)
- Enum constraints (try common enum values; "cannot represent non-enum value: X" confirms the enum name but the value set has to be brute-forced or found via JS bundle inspection)

**Limits:** This does *not* give you a working query result (most queries still need auth). It gives you the schema. With the schema and one auth token, you can then look for IDOR/BOLA/auth-bypass variants.

**On Circle:** Discovered `user`, `users`, `createAccount` mutations, the `SignInCredential` return type, full `CreateAccountInput` shape, and the `CountryCode` enum (whose values are still unknown — Circle uses a non-ISO scheme).

**Introspection-bypass techniques that did NOT work on this Apollo config:**
- Aliases (`s:__schema`)
- `@skip(if:false)` / `@include(if:true)` directives
- Subscription root with `__schema`
- Query batching (Apollo's batching is disabled too)
- Persisted queries (APQ) — `PersistedQueryNotFound` and SHA-mismatch errors did not leak schema

## 4. Next.js `_buildManifest.js` Dumps the Full Internal Route Map (Medium)

**Symptom:** A Next.js app exposes its full client-side route map at `/_next/static/<buildId>/_buildManifest.js` as a JS object literal.

**Detection recipe:**
```bash
# 1. Get the buildId (from any page's __NEXT_DATA__)
curl -s https://target/any-page | grep -oE 'buildId":"[a-zA-Z0-9_-]+'

# 2. Fetch the manifest and extract every route key
curl -s "https://target/_next/static/<buildId>/_buildManifest.js" | \
  grep -oE '\"/[^\"]+\":' | sort -u
```

**On Circle this returned 120+ routes** including:
- `/developer/api-key/create`, `/developer/api-key/[id]`, `/developer/api-key/[id]/edit`
- `/verify-email/[activationToken]`, `/reset-authenticator/[activationToken]`, `/reset-pin-code/[activationToken]`
- `/onboarding/l3/[operationId]/...` (deep KYC flow with ~30 sub-routes)
- `/settings/admin-approvals`, `/settings/ip-allowlisting`, `/settings/limits`
- `/travel-rule/spe/[linkId]/...` (the entire travel-rule compliance flow)

**Why it's a finding (CWE-200):**
- The "hidden" deep-link surfaces are now public — attacker knows the full attack surface
- Routes that may be testable without full auth (e.g. `/verify-email/[activationToken]`) are explicitly listed
- Internal flow names (CPN, Signet, CBIT, CUBIX, XPAY) are exposed
- Pagination of internal-only functionality (e.g. admin approval flow names) is leaked

**Caveat:** Just *having* the routes doesn't mean they're vulnerable. The actual exploit still requires finding an auth check that's missing. But it's the cheapest recon step you'll ever get — 1 GET request yields 120 endpoints.

**Bonus:** The manifest also leaks `__rewrites` and middleware matchers (look for `:nextInternalLocale(en)/...` rewrites — tells you i18n routing). On Circle it also revealed the `__routerFilterStatic` and `__routerFilterDynamic` bit-array params.

## 5. Next.js `.well-known/security.txt` Returns the Full SPA Page (Medium)

**Symptom:** A Next.js page rendered for `/.well-known/security.txt` returns the full 404 SPA page (not the RFC 9116 response) including the i18n JSON, all route names, and the page's `__NEXT_DATA__` JSON.

**Why it happens:** The `app-sandbox.circle.com` is configured to fall through to the SPA shell for any 404, *including* well-known paths. The 404 page is rendered as a full HTML document with all the i18n strings and config inlined.

**What you get on Circle's response:**
- Product name (`Circle Mint`), buildId, environment tags
- Customer support email, sales email, internal help center URL
- Full i18n key map including:
  - All password-validation rules ("Minimum 10 characters", "One lowercase character", ...)
  - All crypto-chain error messages ("Invalid Solana address specified", "Invalid Bitcoin address specified", ...)
  - All MFA factors supported (Okta, Duo, Google Authenticator, 1Password)
  - All KYC country/legal-entity-type codes
  - GraphQL error code map (e.g. `CREATE_TRANSFER_FAILED: { 204: "...", 2007: "..." }`)
  - Internal flow names (CPN, Signet, CBIT, CUBIX)
  - API endpoint hostnames used by the SPA (extracted from the URLs in i18n strings)

**CWE-200 (Information Exposure Through Sent Data) and CWE-200 (Sensitive Information in Source).** Low-severity individually but high-value as reconnaissance for chaining.

**Quick check for this on any Next.js target:**
```bash
for path in /.well-known/security.txt /.well-known/openid-configuration \
            /.well-known/jwks.json /.well-known/oauth-authorization-server \
            /favicon.ico /robots.txt; do
  size=$(curl -s -o /dev/null -w "%{size_download}" "https://target$path")
  echo "$size  $path"
done
# Any path returning a 200 with > 50 KB of HTML is a likely Next.js SPA fallback.
```

## 6. Cloudflare "Lockout" WAF Coverage Map (Updated)

Same WAF coverage table as the Obol reference, with two new entries from the Circle audit:

| Pattern | WAF blocks? | Notes |
|---|---|---|
| `Authorization: Bearer TEST_API_KEY:1':secret` | **Yes (unencoded single-quote triggers Lockout)** | CF SQLi rules catch it |
| `Authorization: Bearer TEST_API_KEY:1%27:secret` | **No (URL-encoded passes through)** | Encoding slips the rule; the API then returns 401 normally |
| `?userId: "{anything}"` with valid arg-name but garbage arg | No (passes to resolver, returns 500) | NoSQLi-style operators in JSON args are unmonitored |
| Apollo Server GraphQL `__schema` queries | No (application-layer block, not WAF) | Introspection must be disabled in Apollo config |
| `static/chunks/.../*.js.map` (Next.js sourcemaps) | Often No | Source maps are public-by-default in Next.js production builds |

**Key insight:** Cloudflare's WAF is **request-pattern** based. It catches SQLi-shaped strings and path-traversal sequences. It does **not** catch:
- URL-encoded variants of blocked patterns
- Object-style operators in JSON args (NoSQLi)
- Per-field validation errors that leak schema info
- Static asset paths (CSS, JS, sourcemaps, manifests)

**Always test the encoding gap.** If `1'` is blocked, try `1%27`, then `1%2527` (double-encoded), then `1''` (empty-quote), then `\u0027` (JSON unicode escape). At least one variant usually slips through.

## 7. Auth-First vs. Validation-First Code Paths (Methodology)

**Symptom:** You send a query to a GraphQL endpoint with a valid-shaped arg, and the server returns a 500 (Internal Server Error) instead of 401 (unauthorized).

**What this tells you:**
- The argument is reaching the *resolver* (not stopped at validation)
- The resolver throws before the auth check, or the auth check fails *after* a pre-auth step
- Likely the pre-auth step is data shape validation, not auth

**Real transcript on Circle:**
```
{user(userId:"not-a-uuid"){id}} → 500 Internal Server Error
{user(userId:"00000000-0000-0000-0000-000000000000"){id}} → 401 Unauthorized
{user(userId:"1"){id}} → 401 Unauthorized
{user(email:"test@test.com"){id}} → 500 Internal Server Error
{user(uuid:"anything"){id}} → 500 Internal Server Error
```

**Implication:** The `user` query takes a `userId` arg (String). It validates the format of that arg (UUID format expected) *before* running the auth check. If the format is wrong, you get 500. If the format is right, you get 401 (because you need to be authenticated to look up any user). This is a *resolver-reachable* endpoint that you can't actually exploit without auth, but the 500 confirms the arg exists and tells you the expected format.

**Disambiguating bypass vs. by-design (extended):**
- 500 on a *valid-shape* arg with a wrong token = the resolver runs, auth check fires afterward
- 401 on a *valid-shape* arg with a wrong token = the auth check fires *before* the resolver
- 200 on a *valid-shape* arg with a wrong token = real bypass (rare; pursue)
- 400 on a *valid-shape* arg with a wrong token = validation rejects the arg shape itself, auth not yet reached

## 8. JS Bundle as a Schema Documentation Source (Methodology)

**Symptom:** You can't run introspection on a GraphQL endpoint, but the SPA has to ship all the queries it uses in its JS bundle. That bundle is the schema documentation.

**Detection recipe:**
```bash
# 1. Get the buildId
curl -s https://target/ | grep -oE 'buildId":"[a-zA-Z0-9_-]+'

# 2. Get the list of all chunks from build manifest
curl -s "https://target/_next/static/<buildId>/_buildManifest.js" | \
  grep -oE 'static/chunks/[a-zA-Z0-9_/\.\-]+\.js' | sort -u

# 3. For each chunk, search for query/mutation operation names
for chunk in $(curl -s ... | grep -oE 'static/chunks/[^"]+'); do
  curl -s "https://target/_next/$chunk" -o /tmp/c.js
  grep -oE "query [A-Z][a-zA-Z]+|mutation [A-Z][a-zA-Z]+" /tmp/c.js | sort -u
done
```

**What you find:** Every query/mutation the SPA uses, including ones not yet exposed in the UI (early-access features, A/B tests, etc.). You also get the *shape* of the query (field selections) which you can use to construct your own queries.

**Caveat:** Production JS chunks are minified, so operation names are mangled. Look for unique error messages or strings instead — anything that doesn't minify (e.g. localized error text) is a stable identifier.

**On Circle this was the path to discovering the full `developer/api-key/create` flow** — the JS chunk for the page referenced the GraphQL operation name and the resolver signature.

## 9. CORS Misconfig with Bearer Auth (Methodology — usually informational)

**Symptom:** A REST API has `Access-Control-Allow-Origin: *` and `Access-Control-Allow-Headers: Authorization`. A CSRF concern.

**Important nuance:** With Bearer-token auth (no cookies), `ACAO: *` is not directly exploitable for cross-origin data theft. The attacker's page cannot read the response because the browser won't send the `Authorization` header cross-origin without an explicit CORS-allow-credentials flow, and `*` precludes `credentials: 'include'`.

**When it IS exploitable:**
- The API also accepts cookies (session-based auth)
- The API has `Access-Control-Allow-Credentials: true` (which would force a specific origin, not `*`)
- An attacker can convince a victim to paste their bearer token into the attacker's page (social engineering)

**Report framing for bounty:** "CORS misconfiguration: the API allows any origin to make authenticated cross-origin requests. While the API uses Bearer-token auth (which limits direct browser exploitation), this is a misconfiguration that violates defense-in-depth and would be exploitable if the API later adds cookie-based auth. CWE-942."

**On Circle:** Found `Access-Control-Allow-Origin: *` + `Access-Control-Allow-Headers: Authorization,Content-Type,X-Request-Origin-Entity-Id,X-Cir-Developerentity-Environment,X-Appinfo,X-Request-Origin-App`. No `Allow-Credentials`. Informational under the Circle bug bounty rules (CORS alone is OOS), but worth noting because the allowed custom headers (`X-Request-Origin-Entity-Id`, `X-Request-Origin-App`) hint at multi-tenant or partner-app routing that may have its own logic.

## 10. Bug Bounty "Out-of-Scope" CORS / Info-Disclosure Rules (Reminder)

Many programs (Circle included) put CORS misconfigurations, missing security headers (CSP, X-Frame-Options), and "informational" info-disclosure findings out of scope. Don't spend your limited time on these unless they:
- Combine with another finding to enable escalation (e.g., CORS + auth leak)
- Are "excessive" info disclosure (full PII, internal credentials, internal endpoints *with* vulnerability)
- Are described in the program's "in scope" list

**Circle's specific OOS categories observed:** CORS, missing security headers, version disclosure, rate-limit findings (unless combined with bypass), SPF/DKIM/DMARC, autocomplete attributes, software version banners. Source: `https://circle.com/en/bug-bounty` (referenced in the audit; not tested here).

## 11. Recon Script for Walled Next.js + Apollo Stack (Recipe)

Composite recipe to use as your first move on any walled Next.js + Apollo Server target:

```bash
TARGET="https://app-sandbox.example.com"
APITARGET="https://api-sandbox.example.com"

# A. Find the buildId
BUILDID=$(curl -s "$TARGET/" -A "Mozilla/5.0" 2>/dev/null | grep -oE 'buildId":"[a-zA-Z0-9_-]+' | head -1 | cut -d'"' -f3)
echo "buildId: $BUILDID"

# B. Extract the full route map
curl -s "$TARGET/_next/static/$BUILDID/_buildManifest.js" | \
  grep -oE '\"/[^\"]+\":' | sort -u | tee /tmp/routes.txt

# C. Sweep the API for 401/404 differential
for p in /v1/payments /v1/transfers /v1/wallets /v1/accounts /v1/balances \
         /v1/cards /v1/payouts /v1/settlements /v1/configuration \
         /v1/users /v1/me /v1/profile /v1/auth /v1/oauth /v1/token; do
  echo "$(curl -s -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0' $APITARGET$p)  $p"
done

# D. Probe the GraphQL endpoint (try common paths)
for path in /api/graphql /graphql /v1/graphql; do
  resp=$(curl -s -X POST "$TARGET$path" -H "Content-Type: application/json" \
    -d '{"query":"{__schema{queryType{name}}}"}')
  if echo "$resp" | grep -qE "Cannot query field|__schema|GraphQL|apollo"; then
    echo "FOUND: $path"
  fi
done

# E. If Apollo, field-probe for queries
for q in user users me viewer session config featureFlags version; do
  resp=$(curl -s -X POST "$TARGET/api/graphql" -H "Content-Type: application/json" \
    -d "{\"query\":\"{$q}\"}")
  if ! echo "$resp" | grep -q "Cannot query field"; then
    echo "EXISTS: $q"
  fi
done

# F. Check verbose error messages on the REST API
curl -s -H "Authorization: Bearer fake:key" "$APITARGET/v1/payments" | head -c 1000
curl -s -H "Authorization: Bearer :::" "$APITARGET/v1/payments" | head -c 1000
```

**Expected output on a typical walled Next.js + Apollo target:**
- A list of 100+ routes from buildManifest
- 5-15 401 endpoints from the REST API sweep
- 1-3 GraphQL endpoints with the Apollo Server fingerprint
- 1-3 verbose error messages leaking format / structure / schema info
- A list of accessible queries/mutations from field-probing

This is the entire unauthenticated recon surface. From here you can write the report or escalate with credentials.

## 12. Limitations of the Unauthenticated Audit (Reminder)

Most impactful bugs in fintech/web3 apps require authentication. For Circle specifically, the following are gated behind auth and cannot be tested without an account:
- IDOR / BOLA on `/v1/payments/{id}`, `/v1/transfers/{id}`, etc.
- BFLA on admin-only mutations
- Business-logic flaws in sandbox USDC mint/transfer flows
- API key regeneration race conditions
- Email-change confirmation bypass
- MFA bypass on `/reset-authenticator/[activationToken]`

**The right play on this kind of target:** Submit the recon findings (verbose errors, schema leakage, CORS misconfig, info disclosure, route enumeration) as a single Medium-severity report titled "Unauthenticated Information Disclosure on Circle Mint Sandbox" with a clear ask for a sandbox account to do the authenticated follow-up. Most programs will grant test access for an audit-quality recon report.

## 13. The "Source Map Leak" / "Build Manifest Leak" Combined Risk (Methodology)

**Symptom:** A Next.js production build ships both the build manifest *and* `.js.map` source maps. The source maps let you decompile the minified JS back to the original source (including all GraphQL operation strings, env variable names, and dev-only function calls).

**Detection recipe:**
```bash
# Check if sourcemaps are exposed
for chunk in $(curl -s "https://target/_next/static/$BUILDID/_buildManifest.js" | \
  grep -oE 'static/chunks/[^"]+'); do
  mapurl="$TARGET/_next/$chunk.map"
  size=$(curl -s -o /dev/null -w "%{size_download}" "$mapurl")
  if [ "$size" != "0" ] && [ "$size" != "404" ]; then
    echo "EXPOSED: $mapurl ($size bytes)"
  fi
done
```

**On Circle:** the JS chunks had a `//# sourceMappingURL=...js.map` comment at the end, suggesting the maps were intended to be public. They were, however, returning 404 in this audit. Worth re-checking on the production target.

**Why it matters (if maps are exposed):**
- Every GraphQL operation string in the original (un-minified) source
- Every environment variable name (sometimes values for NEXT_PUBLIC_ env vars)
- Every internal function/class name
- Every dependency version
- Every developer comment

This is an automatic High finding on most programs. CWE-540 (Inclusion of Sensitive Information in Source Code).
