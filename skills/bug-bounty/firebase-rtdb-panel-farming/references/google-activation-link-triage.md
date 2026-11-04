# Google AI (Gemini) Activation Link Triage

## Why this file exists
A link returned by the Jio/myJio OTP flow is only a *generated* URL. Whether it
can still be redeemed is a separate question that only Google can answer, and
Google will not answer it anonymously. Do not confuse the two.

## Unauthenticated behaviour (measured)
Every `serviceactivation.google.com/subscription/new/<token>` link, fetched with
no cookies, follows the same chain regardless of whether the link is used,
unused, or expired:

```
302 -> accounts.google.com/ServiceLogin?passive=1209600&continue=<original>
302 -> accounts.google.com/v3/signin/identifier?continue=<original>
200 -> sign-in page (~1.25 MB HTML)
```

There is no unauthenticated signal distinguishing the states. Do not try to infer
status from the login page body — words like `invalid` appear in the page's own
JS/CSS and are pure noise. A HEAD request is worse than useless here: it returns
200 on the login page and looks like a healthy link.

## What is required
`cookies_google.json` in the farming directory, in browser-extension format
(a JSON array):

```json
[{"name":"SID","value":"...","domain":".google.com","path":"/"},
 {"name":"HSID","value":"...","domain":".google.com","path":"/"},
 {"name":"SSID","value":"...","domain":".google.com","path":"/"},
 {"name":"APISID","value":"...","domain":".google.com","path":"/"},
 {"name":"SAPISID","value":"...","domain":".google.com","path":"/"},
 {"name":"__Secure-1PSID","value":"...","domain":".google.com","path":"/"}]
```

Only entries whose `domain` ends in `google.com` are loaded. No cookie file means
no triage — report the blocker and stop rather than emitting a guessed status.

## Status taxonomy and decision order
Classify in this order. USED outranks EXPIRED outranks VALID, because Google
renders "already used" copy on pages that also carry redeem wording.

| Status           | Trigger                                                                  |
|------------------|--------------------------------------------------------------------------|
| `LOGIN_REQUIRED` | final URL is `accounts.google.com` containing `signin` or `ServiceLogin` |
| `USED`           | body contains an already-used phrase                                     |
| `EXPIRED`        | body contains an expiry phrase                                           |
| `VALID`          | final host is `one.google.com` or `serviceactivation.google.com` AND body has redeem wording |
| `UNKNOWN`        | landed on a Google host with no known pattern                            |
| `ERROR`          | transport failure                                                        |

Phrase sets (matched case-insensitively):

- **USED**: `already been used`, `already redeemed`, `already claimed`,
  `already activated`, `this offer has already`, `you've already`,
  `offer has ended`
- **EXPIRED**: `expired`, `no longer valid`, `not valid anymore`,
  `offer has expired`, `invalid offer`
- **VALID**: `activate`, `get started`, `redeem`, `claim`, `gemini`,
  `subscription`

## Session hygiene
- Use one `requests.Session` with cookies set per-domain (name/value/domain/path)
  so redirects carry them; a bare cookie header does not survive the hop to
  `accounts.google.com`.
- `allow_redirects=True`, then read `resp.url` — never the request URL.
- Space requests (~1s). Google rate-limits the identifier endpoint, and a wall
  mid-run turns the remaining links into false LOGIN_REQUIRED.
- Report `activation_url_found` from the Jio side as *generated*, never as
  *valid*.
