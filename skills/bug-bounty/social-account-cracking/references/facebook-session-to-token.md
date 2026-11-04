# FACEBOOK SESSION-COOKIE -> ACCESS TOKEN

Web-flow extraction of EAAG tokens from a browser-harvested `Cookie:` string. Complements
references/facebook-bapi-auth.md (mobile-API login), which is the preferred path when
credentials are available.

## Cookie handling
- Parse to dict before any request: split the string on `;`, then `split("=", 1)` per pair.
  Passing the raw string as `cookies=` to `requests` raises
  `TypeError: string indices must be integers` — `cookiejar_from_dict` iterates the string
  per character and indexes it back with a str key. Alternative: set the `Cookie` header
  directly and omit `cookies=`.
- Minimum live cookies: `c_user` + `xs`. `fr`, `sb`, `datr`, `presence`, `ps_l`, `ps_n` help.
- `xs` carries session/IP binding — the same cookies may be challenged from a datacenter IP
  while still valid from the original browser.

## Required header set (bare headers -> HTTP 400 generic error page on every endpoint)
```
User-Agent, Accept, Accept-Language, sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform,
Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User, Upgrade-Insecure-Requests
```
Without this set facebook.com / business.facebook.com answer every path with a ~1.5 KB error
page, which looks like a dead session. Do not conclude anything from a 400 until headers are
correct.

## Leak endpoints (token inline in HTML; session must be live)
- `https://business.facebook.com/business_locations/`  <- primary EAAG source
- `https://business.facebook.com/business_home/`
- `https://business.facebook.com/overview/`
- `https://www.facebook.com/bookmarks/pages/`
- `https://m.facebook.com/` (mobile UA)

Regex: `EAA[A-Z][0-9A-Za-z]{60,}` — EAAG (user), EAAB (app), EAAD (ad), EAAI (iOS app).

## OAuth dialog method (token in redirect Location)
```
https://www.facebook.com/v18.0/dialog/oauth?client_id=<app_id>
  &redirect_uri=fbconnect%3A%2F%2Fsuccess&scope=email%2Cpublic_profile
  &response_type=token&display=touch
```
- Request with `allow_redirects=False`, read `access_token=EAA...` from the `Location` header.
- client_ids seen working: `165907476854626` (Facebook for Android),
  `6628568379` (Facebook for iPhone), `1348564698517390`.
- A redirect to `login.php` = session not authenticated for the oauth flow.

## Liveness markers (check BEFORE probing further)
- live: `"USER_ID":"<non-zero id>"` in the home HTML.
- dead: `"USER_ID":"0"`, any `login.php` redirect, business `loginpage` redirect, or
  `credential_type:"nonce"` + `token:""` in mobile pages (login-form account list — a uid
  there is a suggestion, not a session).

## Validation
```
GET https://graph.facebook.com/v18.0/me?fields=id,name&access_token=<token>
```
`OAuthException` in the response = dead/expired token — drop it, never save it.

## Token economics
- EAAG minted from the business suite is short-lived (~1-2 h). Long-lived conversion:
  `/v18.0/oauth/access_token?grant_type=fb_exchange_token`.
- A `appid|appsecret` string is an APP access token: app-level calls only (`/debug_token`
  etc.), it cannot mint user tokens.

## OPSEC
- Probe once, cleanly: repeated automated hits from a datacenter IP trigger an IP-based
  checkpoint (all endpoints flip to the login form) even though the cookies remain valid.
  A real browser over CDP hits the same wall once the IP is flagged. On a burn, get a fresh
  cookie export instead of retry-hammering.
