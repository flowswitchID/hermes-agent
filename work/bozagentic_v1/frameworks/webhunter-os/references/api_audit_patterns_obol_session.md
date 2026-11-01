# API Audit Patterns — Session-Derived Reference (Obol, 2026-07)

Patterns and pitfalls that surfaced during a real Obol `api.obol.tech` audit. Each pattern is reproducible and worth probing on any REST API with a swagger spec, particularly DVT / validator / airdrop / DeFi registry APIs.

## 1. Filter-Ignoring Search Endpoints (High/Critical)

**Symptom:** A "search" endpoint that the OpenAPI spec documents as requiring `partialLockHash`/`partialClusterName`/`partialAddress` actually returns the full unfiltered database when called with no parameters or with a nonsense parameter.

**Detection recipe:**
```bash
# Spec says required filter; try without it
curl -s -I "https://target/api/search/network" | grep -i content-length
# If Content-Length is huge (KB → MB), the filter is decorative.

# Confirm with a deliberately bogus filter
curl -s "https://target/api/search/network?partialAddress=0xNonExistent" | jq '.total_count'
# If this returns the same total_count as the unfiltered call, the filter is ignored.
```

**Why it happens:** Common backend bug — the controller handler reads `req.query.partialAddress` but if it's `undefined` (no query string at all), the MongoDB/Postgres query becomes `{}` which matches everything. Or the controller builds a filter object but doesn't apply it to the actual query. Sometimes the spec and code drifted apart.

**What to look for in the response:**
- Internal IDs (`_id`, `__v`, `uuid`) — DB enumeration vector
- Cryptographic material: BLS sigs, ENRs, secp256k1 pubkeys, IP hints
- Withdrawal / fee-recipient addresses
- Pre-signed exit messages / deposit data
- Builder/relay registrations
- Internal timestamps, config hashes, UUIDs

**Report framing:** Don't call it "missing auth on read-only data." Frame as: *"The on-chain registry references these by hash only; the raw cryptographic material is internal state. Public exposure enables cluster fingerprinting, targeted operator OSINT, and MEV-Boost correlation. The public registry should serve summaries, not the underlying key shares."*

## 2. NoSQL Operator Injection via Express `qs` Parsing (High)

**Symptom:** A query parameter that's documented as a "substring" filter can be passed as an object and matches the MongoDB query as an operator instead of a string.

**Detection recipe:**
```bash
# URL-encode [$ne] for shell safety
curl -s "https://target/api/search?partialAddress%5B%24ne%5D=nope" | jq '.items | length'
# If this returns ALL items (instead of zero), the API is vulnerable to NoSQLi.

# Also try $gt, $regex, $where
curl -s "https://target/api/search?partialAddress%5B%24regex%5D=.*" | jq '.items | length'
curl -s "https://target/api/search?partialAddress%5B%24where%5D=1" | jq '.items | length'
```

**Why it happens:** Express's default `qs` parser interprets `partialAddress[$ne]=nope` as `{partialAddress: {$ne: "nope"}}` and passes that to MongoDB, which interprets it as a query operator. The fix is to either (a) coerce query types to strings before query, or (b) validate against the expected charset.

**Where else to look:** Any query parameter that takes a "substring" or "filter" string. Try the parameter name with `[]` and `[$ne]` suffixes. The vulnerable parameter is often `id`, `address`, `name`, `email`, `filter`, `query`, `search`, `where`, `partialX`, `q`.

**Cloudflare WAF gap:** WAFs that block `' OR 1=1--` rarely block MongoDB operators. This is a known WAF coverage gap — the attack vector differs from SQL injection's text patterns.

## 3. Auth Contract Violations: 500 Instead of 401 (Medium)

**Symptom:** OpenAPI spec declares `security: [{bearer: []}]` for a route, and the route's documented responses are 200 and 500 (no 401). Actual behavior: returns 500 for missing, malformed, and even valid-format bearer tokens.

**Why this matters:** Either (a) auth is not enforced (the missing-auth path skips the auth guard entirely), (b) the auth dependency throws before validating, or (c) the auth check itself errors. All three are bugs and the spec gives a false sense of security. The 500-on-missing-auth pattern is a strong signal that the auth layer is misconfigured or disabled.

**Detection recipe:**
```bash
# All three should NOT return 500
for token in "" "Bearer xxx" "Bearer 0x0000000000000000000000000000000000000001"; do
  curl -s -o /dev/null -w "%{http_code}\n" "https://target/api/protected" \
    -H "Authorization: $token" -m 10
done
# If you see 500/500/500, the auth contract is broken.
```

**What to do:** Don't claim "auth bypass" without further evidence. The 500 could be a separate downstream failure. But it's worth a Medium report: *"The route's documented security scheme (`bearer`) is not enforced as specified; the missing-auth path returns 500 instead of 401, suggesting the auth guard is either broken or skipped. Recommend auditing the auth dependency and adding a proper 401 handler."*

## 4. Disambiguating "Looks-Like-Bypass" From "By-Design" (Important methodology)

A subtle pitfall: a protected endpoint that returns 400 (e.g., "operator ENR not found") on a garbage bearer can look like an auth bypass, but may actually be a strict auth check that runs **after** an upstream validation step. The error path is misleading.

**How to disambiguate:**
1. Test with the endpoint's actual expected input format (e.g., a real ENR for an ENR-auth endpoint) — if the response changes from "operator not found" to "Authentication verification failed", the auth is being enforced, just on a different code path.
2. Test with two different shape-valid tokens (e.g., a real-format ENR from one operator, a real-format ENR from a different operator) — if both return "Authentication verification failed", the auth is signature-based, not presence-based.
3. Test path/parameter validation order: change the `shareIdx` from invalid (0) to valid (1) with the same garbage bearer. If `0` returns "invalid share index" and `1` returns "operator ENR not found", the validation runs *before* the auth check, which means the auth check still requires a real token — it just hasn't reached it yet.

**False positive trap:** Reporting an "auth bypass" based on garbage-bearer-returns-400 (instead of 401) wastes triage time and burns credibility. Always confirm with a real-format input before claiming bypass.

## 5. Cloudflare WAF Coverage Map (Quick reference)

| Pattern | WAF blocks? | Notes |
|---|---|---|
| `?id=1' OR 1=1--` | Yes (SQLi) | Classic; well-covered |
| `?id[$ne]=1` | No (NoSQLi) | Common gap |
| `?url=http://169.254.169.254/` | Sometimes (SSRF list) | Depends on rule set |
| `?q=<script>alert(1)</script>` | Sometimes (XSS) | Tag-based often blocked; SVG/JS less so |
| `?q={{7*7}}` | No (SSTI) | Often passes through to template engine |
| Path traversal `../../../etc/passwd` | Sometimes | URL-encoded variants often slip through |
| `..; ` (semicolon path) | No | HTTP parameter pollution |

**Always test the WAF gap directly.** Don't assume presence of WAF = coverage.

## 6. Swagger Spec as a Recon Map (Methodology)

For black-box API audits, the OpenAPI / swagger spec is the single highest-value recon artifact. For Obol it exposed:

- The entire 69-endpoint surface in `/docs/swagger-ui-init.js` (191 KB)
- Per-endpoint required vs optional params
- Per-endpoint security schemes (`bearer`, `ApiKeyAuth`, etc.)
- Per-endpoint 401/403/500 response definitions (or their absence — itself a signal)
- Schema definitions for the request/response bodies, which are gold for crafting fuzzing payloads

**Recipe:**
```bash
# 1. Find the swagger-init.js
curl -sI https://target/docs | head -20
curl -s https://target/docs/swagger-ui-init.js -o /tmp/swagger.js

# 2. Extract all paths
python3 -c "
import re
with open('/tmp/swagger.js') as f: c = f.read()
for p in sorted(set(re.findall(r'\"(/[^\"]+)\":\s*\{', c))):
    print(p)
"

# 3. For each interesting path, extract the full operation spec (parameters,
#    request body schema, security, responses) using a regex slice.
```

## 7. False-Positive Checklist for "Read-Only Public Data" APIs

For a registry/lookup API, the following are **not vulnerabilities** even when they look like exposure:

- Returning public on-chain identity (operator addresses, validator withdrawal addresses) for a queried address
- Returning merkle proofs in airdrop/incentive endpoints (proofs must be public to be claimable on-chain)
- Returning per-address badges / tier / effectiveness (public reputation data)
- Returning cluster names and creator addresses (this is a public registry's purpose)
- Returning a "public directory" of operators via a `?page=&limit=` endpoint

What **is** a vulnerability: returning the full DB with no filter, returning cryptographic secret material (BLS shares, ENRs, deposit data, signed pre-signed exits) that isn't part of the on-chain state, returning internal IDs and timestamps that enable DB enumeration.

## 8. Cross-Account Lookup Is Not IDOR

`POST /v1/positions/{network}/{address}` with `additional_addresses: [...]` in the body looks like IDOR but is a **by-design** cross-account query — the Lido protocol fee splitter pattern needs the API to look up positions across multiple addresses in one call. Don't report it as IDOR; instead check whether the response leaks data for addresses the caller doesn't own (it shouldn't, but verify the response shape).
