# Public Graph API dump ("followers" mode, EAAG from the tumbal cookie)

Use when the operator asks for a followers/teman dumper shaped like the
reference tool's `_followers_loop`: prompt for an output file name, prompt for
a profile UID, then paginate `graph.facebook.com` writing `UID|NAME` lines.

## Token prefixes — which one, and where each is used

- `EAAG` — user token scraped from Facebook HTML (the usual working one).
- `EAAT` — business / creator-studio token (page-scoped).
- `EAAB` — mobile-app token.
All three are interchangeable as `access_token=` on `graph.facebook.com`;
scrape with `EAA[A-Z][0-9A-Za-z]{30,}` (prefix-agnostic, longest wins).
- Internal GraphQL (`/api/graphql/`) uses NONE of these — it authenticates with
  the tumbal cookie + `fb_dtsg`/`jazoest`/`lsd`/`av` (see
  `fb-graphql-dump.md`). When the operator asks "EAAG/EAAT/EAAB?" for the
  GraphQL path, the answer is: no access token at all.

## VERIFIED mint recipe (live, 2026-11)

**Only `https://business.facebook.com/business_locations` embeds an EAA token.**
Live probe results: `www.facebook.com/` (45KB feed) EAA=0, `m.facebook.com/`
EAA=0, `mbasic.facebook.com/` EAA=0, `business_locations` (~1.3MB) EAA=1.
That one token is a real 197–199-char `EAAG…` user token that verifies against
`/v18.0/me` (returns the tumbal's own `c_user` id + name). It **rotates per
page load** (same ~20-char prefix, different tail/length each request) — mint
fresh, don't cache across sessions without re-verifying.

```
GET https://business.facebook.com/business_locations
    (UA from the accepted pool, session carrying the tumbal cookie)
regex EAA[A-Z][0-9A-Za-z]{30,}  ->  take the longest match
```

**The cookie must travel with the token.** `GET /v18.0/me?…&access_token=<t>`
with only a UA header returns `{"error": "Invalid request."}` from a datacenter
IP; the same request with `cookies=<session jar>` returns id+name. Any
verification/edge call must pass both.

## What the minted token actually gets you (verified)

`/v18.0/me/permissions` on this token class: **~80 granted permissions**
(ads_management, business_management, pages_*, instagram_manage_*, whatsapp_
business_*, threads_*, read_insights, read_custom_friendlists, offline_access).
It is long-lived (`offline_access` present).

`/v18.0/me/accounts` returns the tumbal's owned Pages **with page-scoped
tokens** — save `page_id|page_name|page_token` to `.pages.txt`; page edges
(`/<page_id>/feed`, `?fields=fan_count`) work with them.

Dead edges on this token (verified): `/me/friends` and `/<uid>/friends` return
`data: []` (user_friends not granted — v2.0 restriction), `/me/friendlists`
returns `(#100) nonexisting field` (edge removed), `/me/subscribers`
deprecated, `/me/taggable_friends` permission denied. Do not build the
followers mode on Graph API edges for a target's friend list — cookie-only
internal GraphQL remains the path that yields (see `fb-graphql-dump.md`).

## Token verification + caching

Verify before use: `GET /v18.0/me?fields=id,name&access_token=<t>` **with the
cookie jar** → `id,name` means alive; an `error` payload means dead. Cache
minted tokens next to the script (`.t.txt` EAAG, `.g.txt` EAA) and the cookie
in `.c.txt`; on startup load-and-verify, re-mint from the cached cookie
silently when verification fails, and only prompt for a new cookie when
minting also fails.

`debug_token` is useless here: with a non-owner app token it returns
`(#100) You must provide an app access token, or a user access token that is an
owner or developer of the app`. Verify with `/me` instead.

## EAAT minting via device-login (when scraping yields nothing)

Verified flow and its one hard blocker:

1. `POST https://graph.facebook.com/v18.0/device/login/` with
   `access_token=<app_id>|<app_secret>` and scopes (ads_management,
   pages_manage_ads, business_management, public_profile, email, user_friends)
   → returns `code` (long), `user_code` (short, shown to the user), `interval`.
2. Confirm on **`https://m.facebook.com/device?user_code=<user_code>`** —
   m.facebook.com renders the real form; mbasic redirects away. Walk the
   form's hidden inputs, add `user_code`, POST to `form['action']` on the same
   host with `Referer` set (the action is `/device/redirect/`).
3. Poll `GET https://graph.facebook.com/v18.0/device/login_status`
   **`?method=post&code=<long code>&access_token=<app_token>`** — the
   `method=post` param is required; without it Graph answers
   `(#100) nonexisting field (login_status)`. "pending action" means the
   consent step has not completed yet.
4. **Blocker:** the consent dialog returns "Terjadi kesalahan saat Anda masuk
   ke aplikasi ini" for any app the tumbal is not an admin/tester of (the
   usual pooled tokens are dev-mode apps owned by someone else). Device-login
   EAAT requires the operator's OWN app token (put `APPID|SECRET` in
   `.apptoken` or env `FB_APP_TOKEN`) with "Login from Devices" enabled.
   Classic dialog/oauth is dead: it redirects to `encrypted_query_string`
   which needs a real browser.

EAAT (short-lived) → EAAG (long-lived) exchange:
`GET https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=<id>&client_secret=<secret>&fb_exchange_token=<short>`
(cookie jar optional). Only works with the operator's own app.

## Request + pagination

```
GET https://graph.facebook.com/v18.0/<uid>/<edge>
    ?fields=id,name&access_token=<token>&limit=5000   (+ cookie jar)
follow paging.next; stop when data is empty OR a page adds no fresh uid.
```

Graph tier is cheap: ~0.4s + jitter per request (HTML tiers stay slower).

## Edge fallback order — the fix over the reference

The reference hardcodes a single edge (`/friends`) and the whole mode dies
when FB returns `{"data":[]}`. Use `followers -> friends -> subscribers` and
drop to the next edge when the current one yields zero; stop at the first edge
that produces anything.

## Restart-safe dedup

Preload existing UIDs from the output file into the seen-set at construction.
The reference keeps the set in memory only, so every restart re-dumps and
re-writes the first page. A dedup set that survives restart is the difference
between append and re-dump.

## Output path (operator runs on Android/Termux)

Accept a bare `name.txt`; prefix `/sdcard/` only when `/sdcard` actually
exists, otherwise resolve against cwd. Reject `/sdcard` and `/sdcard/` as
bare inputs (the reference loops forever on them). Validate the final path
with `open(path,'a').close()` before dumping.

## Wiring

Add a mode selector right after the cookie prompt (recursive UID dump vs
followers dumper) instead of shipping a second script, and expose the same
mode as a CLI flag (`--followers UID`) that accepts either a cookie (auto-mint)
or an explicit `--token`.

## Honesty about yield

`/friends` returns only app-authorized friends (user_friends); `/followers`
and `/subscribers` depend on token scope. When all three edges return empty,
say so and fall back to the internal-GraphQL/HTML ladder — never present
public Graph API as the primary path for dumping a stranger's friend list.

## Pitfall: stateful fakes when testing paginated loops

When unit-testing a paginated dumper, the fake session must be built ONCE and
cached. A `session()` that rebuilds the fake HTTP object resets the page
cursor to 0, every request returns page 1 again, and the test then "passes"
the pagination check while only ever exercising page 1 — totals come out short
and the bug hides. Assert on request count AND the URLs actually fetched, not
just the final count.
