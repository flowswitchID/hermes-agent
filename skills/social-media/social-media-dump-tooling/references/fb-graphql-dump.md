# Facebook internal GraphQL UID dump (API-first, anti-checkpoint)

Use when the operator asks for an API-based UID dump (not mbasic/HTML), or
complains that mbasic crawling hits checkpoints fast.

## Why public Graph API is a dead end for this

Since Graph API v2.0, `GET /<uid>/friends` only returns friends who ALSO
authorized the same app (`user_friends`). For dumping a stranger's friend
list it returns empty. Never sell it as the primary path — it is a bonus
pass only when a token is supplied (`/subscribers`, `/followers` sometimes
return more).

## The real API path: internal GraphQL

`POST https://www.facebook.com/api/graphql/` — same endpoint FB's own web
client uses. Cursor-paginated, small payloads, far more tolerant than
mbasic HTML (no page-size heuristics, no markup to parse). Upstream
`urls.so` of the CURL-XD family carries the constants `GRAPHQL` and
`RFOLLOWS`, confirming the original tool uses this route.

### 1. Warm-up — harvest auth material

GET `https://www.facebook.com/` (www, desktop UA) once with the tumbal
cookie, extract:

```
fb_dtsg : name="fb_dtsg" ... value="..."   |  "fb_dtsg":"..."
          |  "DTSGInitialData",[],{"token":"..."}
jazoest : name="jazoest" ... value="(\d+)"   |  "jazoest":(\d+)
lsd     : name="lsd" ... value="..."         |  "LSD",[],{"token":"..."}
user    : "USER_ID":"(\d+)"                  |  fallback: cookie c_user
```

`jazoest` fallback (when not in HTML): `str(2 + sum(ord(c) for c in fb_dtsg))`.

### 2. Harvest doc_id + friendly_name pairs from the same HTML

```
"doc_id":"(\d{10,25})"[^{}\n]{0,300}?"friendly_name":"([A-Za-z0-9_]+)"
"friendly_name":"([A-Za-z0-9_]+)"[^{}\n]{0,300}?"doc_id":"(\d{10,25})"
"query_name":"([A-Za-z0-9_]+)"[^{}\n]{0,300}?"doc_id":"(\d{10,25})"
```

CRITICAL: the gap must exclude `\n` — without it the lazy match skips across
lines and pairs friendly_name from line A with doc_id from line B (silent
wrong pairing). Prefer candidates matching
`/(?i)friend|follower|subscri|profilelist|peopleyou/`; doc_ids rotate, so
harvesting beats hardcoding. Keep a candidate cap (~8).

### 3. POST body

```
av, __user = c_user uid
fb_dtsg, jazoest, lsd = harvested
fb_api_req_friendly_name = <friendly_name>
variables = json.dumps({...}, separators=(',',':'))
server_timestamps = true
doc_id = <doc_id>
header: X-Fb-Lsd: <lsd>
```

Response may be prefixed `for (;;);` — strip before `json.loads`.

### 4. Variables — try several schemas, first non-empty wins

```
{'count':30,'cursor':CUR,'scale':1.5,'id':uid}
{'count':30,'cursor':CUR,'profileID':uid,'scale':1.5}
{'count':30,'cursor':CUR,'userID':uid,'scale':1.5}
{'count':30,'cursor':CUR,'profile_id':uid,'scale':1.5}
{'count':30,'cursor':CUR,'actorID':uid,'scale':1.5}
{'count':30,'cursor':CUR,'pageID':uid,'scale':1.5}
```

### 5. Response parsing — recursive walkers, no fixed paths

```
pairs  : walk dicts; a node with .id (9-20 digits, int OR str) plus
         .name (or .title.text) is a hit. Deepest/longest name wins.
cursor : walk dicts for page_info; only accept
         {has_next_page: true, end_cursor: ...}
```

Also accept int ids — FB returns `"id":100012345678` unquoted in GraphQL
JSON. Regex-only parsers tuned for quoted strings silently miss those.

## Strategy ladder (anti-checkpoint)

`graphql -> graph (if token) -> www HTML -> mbasic HTML`. Only fall through
a level when the previous one yielded ZERO pairs. mbasic stays as last
resort: it is the path that trips checkpoints fastest. Wall detection by
markers only (`login_form`, `temporarily blocked`, `checkpoint`, `captcha`,
`/login`...) — NEVER by page size, a small page is not a wall. Per-level
delay: graphql 0.7s, www 1.5s, mbasic 2.5s (+ jitter, proxy rotation).

## Checkpoint reality

mbasic -> checkpoint fast is real, but no API route removes it entirely:
fb_dtsg is tied to the session and aggressive depth-2 recursion (5 workers
x hundreds of uids) will still trip walls regardless of transport. Keep
`max_uids` cap, dedup queue (never re-crawl a uid), and `--proxy-file`
rotation as the actual mitigations. Tell the operator the truth: GraphQL
lowers the wall-hit rate, it does not eliminate it.