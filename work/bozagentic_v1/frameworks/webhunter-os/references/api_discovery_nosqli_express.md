# API Discovery & NoSQLi Fingerprinting — Session-Derived Patterns

## 1. API Discovery Pipeline

### Layer 1: robots.txt → Internal Endpoints
robots.txt often exposes paths the SPA doesn't advertise:

```
Disallow: /webapi/
Disallow: /service_api/
Disallow: /my-servers
Disallow: /my-orders
Disallow: /balance
Disallow: /api-keys
Disallow: /ssh-keys
Disallow: /2fa
Disallow: /hive-login
Disallow: /docker-auth
```

**Rule**: robots.txt `Disallow` entries are attack surface hints. Many paths listed there are **not** truly secret — they're just gated behind auth.  
**Check**: `curl -sI $TARGET/robots.txt` → parse `Disallow:` lines → probe each.

### Layer 2: JS Bundle Analysis → Hidden API Routes
Next.js/Vite/SPA bundles contain route configs and API paths. Extraction techniques:

| Pattern | What to Find |
|---------|-------------|
| `["'`]`/path/to/api`["'`]` in JS | Hardcoded API paths |
| `routes`/`paths` config objects | Client-side routing table |
| `"` + keyword + `"` in string literals | Market data endpoints (marketplace, servers, orders, balance) |
| `fetch("` + relative path | Direct API calls |
| Base URL configs | `apiUrl`, `baseUrl`, `backendUrl` assignments |

**Next.js specific**: `_buildManifest.js` contains rewrite rules → `(?<key>\d+):"(?<path>/api/[^"]+)"`

**Express/NestJS backend**: Root endpoint `GET /` returns `{"environment","mode","version"}` — hit it to confirm stack.

### Layer 3: Subdomain Enumeration → Separate API Backend
Targets often have `api.target.com` as a separate nginx/Express server:

```bash
curl -sI https://api.target.com/ | grep -i server
# → nginx/1.24.0 (Ubuntu) — different stack than main site
```

Check paths like `/v1/`, `/v2/`, `/api/`, `/graphql` on the API subdomain.
If `/v1/marketplace` returns data while other `/v1/*` return `{"code":3}`, the marketplace endpoint is intentionally public.

### Layer 4: Swagger/OpenAPI Discovery
Common paths that expose API documentation:

| Path | Framework |
|------|-----------|
| `{base}/docs` | Swagger UI (NestJS, Express) |
| `{base}/docs/json` | OpenAPI spec as JSON |
| `{base}/api-docs` | Swagger 2.0 |
| `{base}/swagger.json` | Swagger 2.0 |
| `{base}/openapi.json` | OpenAPI 3.x |
| `{base}/v2/api-docs` | Spring Boot |

**Probe pattern**: Try `GET` each on every subdomain + main domain. Even if `/docs` is behind the SPA, check if the docs endpoint on the backend subdomain is exposed.

### Layer 5: Direct Endpoint Testing
Once paths are discovered, test with both GET and POST. Many endpoints that return HTML via GET (`Cannot GET /api/endpoint`) accept JSON via POST.

## 2. NoSQL Injection Testing via Error Analysis

The response to malformed JSON input differentiates auth-gated endpoints from injection-vulnerable ones.

### Response Taxonomy

| Input Type | "Permission denied" | "Internal Server Error" (500) |
|------------|-------------------|-------------------------------|
| `{"token": "any_string"}` | ✅ Validation passed → token invalid | ❌ Not applicable |
| `{"token": {}}` (object) | ❌ Rare — means strict type check | ✅ **MongoDB attempted the query with an object operator** |
| `{"token": []}` (array) | ❌ Rare | ✅ Array parsed → query attempted |
| `{"token": {"$ne": ""}}` | ❌ (would mean NoSQLi succeeded) | ✅ **$ne operator reached MongoDB but crashed** |
| `{"token": {"$regex": ".*"}}` | ❌ | ✅ **Regex engine attempted** |
| `{"token": {"$gt": ""}}` | ❌ | ✅ **$gt reached DB layer** |
| `{"token": {"$exists": true}}` | ❌ | ✅ **$exists parsed** |
| `{"token": {"$where": "1==1"}}` | ❌ | ✅ **$where attempted** |
| Missing field `{}` | ❌ | ✅ Field validation failed |

### Interpretation

- **"Permission denied"** → Server validated the input as a string, found the user/query, but the token is wrong. Means input is sanitized before DB query.
- **"Internal Server Error"** (only for operators, not for strings) → MongoDB operators are reaching the query but crashing. The crash can be from:
  - The `token` field being a non-string vs string field in the schema
  - A string-comparison index that rejects object queries
  - The returned document having an unexpected shape
- **"Internal Server Error" for ALL inputs** → No MongoDB involved, or different error handling path.

### Key Signal

If `"token": "test"` → `403 Permission denied` but `"token": {"$ne": ""}` → `500 Internal Server Error`, the backend **IS running MongoDB** and the operators are reaching the query layer. The crash means either:
- The field is indexed/typed as string-only
- The query returns a document that can't be processed
- Input validation crashes before the query

If ALL operator payloads return 500 (including `$eq`, `$exists`), the injection path is likely **dead** — the server validates the JSON structure before calling MongoDB.

## 3. Express/NestJS API Fingerprinting

| Signal | Backend |
|--------|---------|
| Root `GET /` returns `{"environment","mode","version"}` | NestJS / Express |
| Sub-routes return `{"message":"Route GET:...","error":"Not Found","statusCode":404}` | NestJS / Express route-routing |
| Root `GET /` returns default nginx page | Static nginx (no app) |
| Redirect `location: /` with root path | Simple nginx reverse proxy |

### Express Route Pattern

NestJS apps follow: `/{base}/{controller}/{action}`
- `{base}` — e.g. `bot-api`, `poh-api`, `v1`
- Root `GET /{base}/` returns version info
- Unknown routes return structured JSON errors, not HTML

## 4. Sails.js Development Mode Detection (from Kuant.ai)

| Signal | Where |
|--------|-------|
| `SAILS_LOCALS._environment = 'development'` in HTML | Every Sails page |
| `/api/health` returns `"environment":"development"` | Health endpoint |
| `X-Server-IP: 172.17.0.x` header | Docker internal IP leak |
| Default Sails homepage `NEW_APP_NAME` in title | Fresh dev deploy |
| Blueprint API routes (e.g. `GET /user`, `GET /model`) | Auto-generated in dev |
| Socket.io at `/socket.io/` but returns `"Transport unknown"` | Transport blocked by reverse proxy |

## 5. CORS Assessment Pattern

**`Access-Control-Allow-Origin: *` alone is NOT a vulnerability** for token-based auth. It only matters when:
- `Access-Control-Allow-Credentials: true` is also set (cookies/auth-required)
- The API uses cookie/session-based auth instead of Bearer tokens
- Combined with authenticated endpoints that return sensitive data

Check with:
```bash
curl -sI -H "Origin: https://evil.com" $ENDPOINT | grep -i access-control
```

✅ `Access-Control-Allow-Origin: *` = OK for public APIs  
❌ `Access-Control-Allow-Origin: *` + `Access-Control-Allow-Credentials: true` = CRITICAL  

## 6. False Positive Guard: Marketplace/Listing APIs

**Marketplace/listings/public-data endpoints are usually INTENDED to be public.**

If a GET endpoint returns product listings, server availability, pricing, or public profiles, check:
- Is the data shown on the public website without login? → **Intended**
- Are there fields exposed that the website doesn't display? → **Data over-exposure**
- Are internal IDs (owner_id, server_id) exposed that enable enumeration? → **IDOR chain potential**
- Is the data cached/CDN-served? → **Not a bug**

**Sequential IDs in public responses are NOT bugs.** They only become bugs if:
- A privileged endpoint (user balance, private profile) uses the same ID format
- An authenticated endpoint trusts the ID without ownership verification
- The ID exposes a count/growth metric the platform considers sensitive

## 7. Bot API / Internal Service Risk Assessment

When an internal API (e.g. `bot-api`, `poh-api`, `service-api`) is found:

**Checklist:**
1. Is it documented? (Swagger/docs)
2. Does it require real auth or just a token field in the body?
3. What operations does it expose? (message/email send → abuse/SPAM, account/link → account takeover)
4. Can we enumerate valid tokens?
5. Is NoSQL injection possible? (see section 2)
6. Does the root endpoint return version info?
