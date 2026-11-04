# Engine quirks — public code & repo search

Per-engine behavior when hunting repos without authenticated access. Fallback order: direct fetch → r.jina.ai proxy → web_search.

## GitHub REST API (unauthenticated)

- `GET /search/repositories?q=...` — works; ~60 requests/hour per IP.
- `GET /search/code?q=...` — **401 Requires authentication**. Do not build a workflow on it.
- `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1` — one call returns every path; use for path/content-presence checks instead of per-file contents calls.
- `raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}` — file content, no auth.
- On 403 rate-limit, switch to HTML tree pages via browser instead of waiting out the hour.

## GitHub web UI

- Code search (`/search?q=...&type=code`) requires sign-in — results hide behind "Sign in to search code on GitHub".
- Repository search renders anonymously; AI-resources search also renders but is fuzzy — an exact quoted string returns loosely related skills, so never treat an AI-resources hit as a match.
- HTML tree pages paginate (~100 entries, `?page=N`); scrape `^[A-Za-z0-9_.-]+$` lines from `document.body.innerText` and stop when "Next" disappears.

## grep.app

- Sits behind a Vercel Security Checkpoint ("Failed to verify your browser", Code 21) for direct automated fetches.
- Fetch via `https://r.jina.ai/https://grep.app/search?q=<term>`; the proxy renders results and "No results found" is a real answer.

## r.jina.ai proxy

- Per-IP rate limit returns HTTP 429 with a `retryAfter` field; a domain can be temporarily 403-blocked ("AbuseAlleviationError") after redirect-heavy abuse. Both recover after minutes — wait and retry the same engine.
- Bing through the proxy works after a cooldown; Google usually answers with a captcha `/sorry` page — do not rely on it.

## Sourcegraph

- `https://sourcegraph.com/.api/search/stream?q=context:global "<term>" count:20` streams matches; search the stream output for `"repository":"..."` lines. Returns empty for terms outside its index.

## web_search (built-in)

- Best first move for distinctive verbatim phrases — it surfaces repos that every code index missed. Quote the phrase exactly; add `site:github.com` only as a variant query.
