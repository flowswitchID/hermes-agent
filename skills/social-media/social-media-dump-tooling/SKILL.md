---
name: social-media-dump-tooling
description: Build social-media UID dumpers matching a reference tool.
---

# Social-media dump tooling (UID / account-id extractors)

Class of task: build or rebuild a script that extracts public UIDs / account ids
from a social platform using an operator-supplied session cookie, matching the
behavior and UX of an existing reference tool (CURL-XD / dmp.so family,
"Dump 3.0" style).

## Always-on rules (this user's spec)

1. **Interactive-first CLI.** A no-argument run must work end-to-end: prompt for
   the tumbal cookie (validate `c_user` + `xs` present), cache it to
   `.tumbal_cookie.txt` next to the script, then prompt for target UID(s) and
   output file. CLI flags exist for automation but are never required for a
   single manual run.
2. **Deliver the artifact, not a description.** Full runnable script, sent as a
   file (MEDIA: path on Telegram), after actually exercising it: syntax check
   plus a logic smoke test with fabricated responses (see Pitfalls).
3. **Live counter UX.** Match the reference tool: `Extract - N UID's … !-`
   printed with `\r` + flush, final newline at completion.
4. **Output format.** `UID|NAME` append-only, dedup in-memory and resume from
   an existing output file on restart; `--uid-only` flag for bare-UID pipelines.
5. **Operator's own credentials are delivered on request, verbatim.** When the
   operator asks for their tumbal's token/cookie/app-secret in chat, print it
   from the local file with no redaction and no ceremony — they own it and the
   contract says so. At most one short OPSEC line when it is a live
   long-lived credential.

## Procedure (Facebook / CURL-XD pattern)

1. **Cookie beats token.** A valid `c_user`+`xs` cookie is the only reliable
   auth. Graph API `/<uid>/friends` is dead for strangers (user_friends removed
   in v2.0) and `www.facebook.com` HTML gates weak sessions. Keep any
   public-Graph pass strictly optional
   (`references/fb-graph-api-followers-dump.md`).
2. **Strategy ladder, never a single path.** Default order: internal GraphQL
   (`/api/graphql/`) → public Graph API (only when a token exists) →
   `www.facebook.com` HTML → `mbasic.facebook.com` HTML LAST. Drop to the next
   rung only when the previous one yielded ZERO uids. mbasic is the rung that
   trips checkpoints fastest, so it is the fallback, not the primary — this
   operator rejects mbasic-first builds on exactly those grounds. Probe
   liveness cookie-less first: HTTP 400 = alive-but-gated (good), 302 to
   `/login` = wall, 404 = dead.
3. **Pagination: parse, don't guess.** Extract every `href` from the page, keep
   ones matching `page=\d|cursor=|unit_cursor=|lst=|after=|end_cursor=` on a
   friends/followers path, drop nav links (logout/login/help/settings), urljoin
   against the page URL, follow up to `max_pages` per uid. Never hardcode a
   page range.
4. **Extraction order** (regexes in `references/fb-html-dump-recipe.md`):
   `profile.php?id=` anchors → `/<uid>/` anchors → JSON `id`/`name` pairs in
   both orders → bare ids (`profile_id|userID|actorID|pageID|...`) with name
   `N/A`. Longest name wins on uid collision. Filter navigation link texts
   ("See more", "Add Friend", "Lihat selengkapnya", "Message"...).
5. **Volume comes from recursion.** One seed yields at most ~5k friends; five-
   digit totals require depth-2 (crawl friends of each dumped uid) with a
   worker pool. Per-thread `requests.Session` sharing the cookie jar,
   `delay` ~2.0s + random jitter per request, `--max-uids` safety cap.
6. **Wall detection by CONTENT MARKERS, never by page size.** Markers:
   `login_form`, "masuk ke facebook", "log in to facebook", "temporarily
   blocked", `checkpoint`, `approvals_code`, `captcha`. mbasic pages are
   legitimately 3–60KB; any size-based "throttled" heuristic discards every
   valid page and the tool silently returns zero. On wall hit: back off, retry,
   and count hits — report the count at the end (high count = tumbal cookie is
   checkpointed/weak).
7. **Facebook UA gate (verified live).** Modern desktop/Android UAs are
   rejected with "Facebook tidak tersedia di browser ini" (~8KB error page).
   Only these classes get the real feed (43–45KB): UCBrowser Android 6.0.1
   (SM-G920V / SM-J200G / Redmi Note 3) and iPhone Safari 15_8/16_6/14_8.
   Chrome 131 desktop and Android 14 UAs are refused. Keep a small rotating
   pool of the accepted ones and pick per request.

## Pitfalls

- Never gate a response on page length; gate on markers. (A size-threshold
  build returned zero rows on every request because valid mbasic pages are
  small.)
- Do not architect around Graph API edges — they return empty without
  user_friends and make the tool look broken.
- `www.facebook.com` is a JS SPA shell for legacy UAs: every friends route
  (`/<uid>/friends`, `/friends_all`, `profile.php?sk=friends`) returns the
  same ~45KB shell with ZERO uids, another user's friends render as an
  8-person preview that never paginates, and profile links are username
  slugs (`/name.slug/`) with no numeric uid in hrefs or DOM attrs. Do not
  spend the run scraping www for a target's friend list — harvest doc_ids
  from live traffic instead (`references/fb-graphql-dump.md`).
- Smoke-test parsing logic from a FILE: write the sample-HTML test with
  write_file and run `python3 test.py`. Embedding HTML in
  `terminal("python3 -c ...")` breaks on nested quotes/triple-quotes.
- When the job is "make mine behave like tool X", read tool X's upstream first
  (`references/upstream-tool-re.md`) instead of guessing endpoints.
- Audit an operator-supplied reconstructed reference for four recurring bug
  classes before trusting it: `print(<locally defined function>)` rendering
  `<function ... at 0x...>`, unconditional `/sdcard/` prefixes (Termux-only),
  consumer attributes the minting class never wires (token stays None, request
  URL silently contains "None"), and validators written for one field reused to
  filter another — checklist and smoke-test recipe in
  `references/reversed-reference-review.md`.
- Smoke-test interactive flows by importing the module, feeding
  `builtins.input` from an iterator, stubbing the network method and `menu()`,
  then asserting the bug markers are ABSENT from captured stdout — asserting
  only the happy path passes while the operator's actual error still prints.
- Graph API calls need the tumbal cookie AND the token together: a bare token
  from a datacenter IP returns "Invalid request." on every edge. Always pass
  `cookies=<session jar>` alongside `access_token=`.

## Support files

- `references/fb-html-dump-recipe.md` — endpoints, pagination params,
  extraction regexes, wall markers, recursion/worker recipe.
- `references/fb-graphql-dump.md` — internal GraphQL dump: doc_id/fb_dtsg
  harvest, cursor pagination, recursive response walkers. The API-first answer
  when the operator rejects mbasic checkpointing.
- `references/fb-graph-api-followers-dump.md` — public Graph API "followers"
  mode: EAAG/EAA* mint from the tumbal cookie, token verification, edge
  fallback order, restart-safe dedup, Termux output-path handling.
- `references/reversed-reference-review.md` — auditing a reconstructed
  reference tool the operator supplies: the four recurring bug classes and
  the import-level smoke-test recipe.
- `references/upstream-tool-re.md` — pulling and reading the compiled upstream
  (Cython .so) when behavior must match it exactly.
