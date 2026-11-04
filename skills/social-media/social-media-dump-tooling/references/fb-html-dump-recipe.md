# Facebook HTML dump recipe

Depth-only reference for `social-media-dump-tooling`. All URLs assume a valid
`c_user` + `xs` cookie in the session.

## Endpoints

| Purpose | URL |
|---|---|
| friends list (primary) | `https://mbasic.facebook.com/<uid>/friends` |
| followers / following | `https://mbasic.facebook.com/<uid>/followers` `/following` |
| mutual friends | `https://mbasic.facebook.com/<uid>/mutualfriends` |
| www fallback | `https://www.facebook.com/<uid>/friends?page=N` |
| profile lookup | `https://mbasic.facebook.com/profile.php?id=<uid>` |

## Headers that matter

Mobile Android Chrome UA with a real device token in brackets
(`... Mobile Safari/537.36 [SM-G991B]`), `Accept-Language: id-ID,id;q=0.9`,
`Sec-Fetch-*: same-origin/navigate`, no `Accept-Encoding` when relying on
`r.text` (br/zstd undecodable by requests).

## Pagination link filter

Keep hrefs matching `(page=\d|cursor=|unit_cursor=|lst=|after=|end_cursor=)`
AND `(friends|followers|subscribers|mutual)`; drop
`(logout|login|help|settings|privacy|home\.php)`. urljoin against the current
page. Cap per-uid (`--pages`, default 8).

## Extraction regexes

```
profile anchor : <a[^>]+href="[^"]*?profile\.php\?id=(\d{9,20})[^"]*"[^>]*>(.*?)</a>
path anchor    : <a[^>]+href="/(\d{9,20})(?:[/?"][^"]*)?"[^>]*>(.*?)</a>
json id,name   : "id":\s*"?(\d{9,20})"?\s*,\s*"name":\s*"((?:[^"\\]|\\.)*)"
json name,id   : "name":\s*"((?:[^"\\]|\\.)*)"\s*,\s*"id":\s*"?(\d{9,20})"?
bare ids       : "(?:profile_id|userID|actorID|actor_id|ownerID|pageID|delegate_page_id|targetFBID|uid)":\s*"?(\d{9,20})"?
```

Clean names: strip tags, `html.unescape`, collapse whitespace. Reject nav texts
(case-insensitive): `see more|lihat selengkapnya|add friend|tambah teman|
confirm|konfirmasi|message|pesan|friends?|teman|mutual friends?`.

## Wall markers (any one = wall, not throttled)

`login_form`, `masuk ke facebook`, `log in to facebook`, `you must log in`,
`temporarily blocked`, `checkpoint`, `approvals_code`, `captcha`,
`suspicious activity`, `href="/login"`.

## Recursion / worker recipe

```
queue: (uid, depth); depth 1 = seeds
worker: GET mbasic/<uid>/friends + pagination -> pairs -> store.add()
        if depth < max_depth: enqueue every new uid at depth+1
stop:   store.total >= max_uids
```

Per-thread `requests.Session` (cookie jar per thread), `delay + uniform(0, 1.2)`
sleep before each request, `max_uids` cap (default 200k), `workers` default 5.

## Graph pass (optional, only if a token is supplied)

`https://graph.facebook.com/v18.0/<uid>/<edge>?fields=id,name&access_token=...`
edges: `friends`, `followers`, `subscribers`; follow `paging.next`. Expect empty
for `friends` without user_friends — never depend on it. The API-first answer
to "Graph API is dead / mbasic checkpoints fast" is internal GraphQL
(`/api/graphql/`), not public Graph API — see `references/fb-graphql-dump.md`.
