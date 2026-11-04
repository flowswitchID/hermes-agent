# FACEBOOK b-api auth.login — WORKING CONTRACT

Reference implementation for social mobile-API credential testing. Contract is versioned:
re-harvest from a current APK before relying on it (see SKILL.md step 1).

---

## Endpoint

```
POST https://b-api.facebook.com/method/auth.login
```

Unlike the GraphQL/Bloks web path, this endpoint needs no session bootstrap — it accepts
`access_token`/`api_key` params directly, which is why it replaced the old method in the
operator's tooling.

## Request shape

```
api_key=<harvested from current APK>   # versioned, e.g. 62f8ce9f74b12f84c123cc23437a4a32
email=<uid>
password=<pass>
credentials_type=password
format=json
generate_machine_id=1
generate_session_cookies=1
locale=en_US
method=auth.login
return_ssl_resources=0
v=1.0
```

Headers: `User-Agent: [FBAN/Orca-...;]` (Dalvik/2.1.0 style), `Content-Type:
application/x-www-form-urlencoded`.

**Never store the api_key value** in notes or skills — it rotates with app versions. Record the
source field in the decompiled APK instead.

## Response classification

| Response | Meaning | Action |
|---|---|---|
| `error_msg == "Invalid username or password"` (code 401) | bad creds | continue loop |
| `error.code == 405` / `"Invalid parameters"` | request shape wrong | **stop and fix**, not a result |
| `error.code == 406` / `"Login approvals"` | 2FA / checkpoint approval | checkpoint bucket, live account |
| `error_subcode == 134816` / checkpoint payload | account checkpointed | checkpoint bucket |
| `access_token` + `cookies` present | success | session bucket, reuse cookies |
| HTTP 200 with `session_key` / `uid` | success variant | session bucket |

- Cookies from `generate_session_cookies=1` replay directly against `b-api.facebook.com` —
  follow-up actions reuse the session, no re-login.
- `machine_id` from `generate_machine_id=1`: reuse the SAME machine_id for all attempts of one
  target; a rotating machine_id per attempt looks like device-farming and triggers checkpoints.
- Indonesian mobile prefixes (`+62`, MNC 510/511/512...) map to operator/region hints when the
  response includes region fields — keep the mapping table with the tool, not in the skill.

## Why this method over GraphQL Bloks

- No `lsd`/`jazoest` token bootstrap — those live only seconds and break long runs.
- No GraphQL `doc_id` rotation every release.
- Stable JSON response shape — classification is a pure dict lookup, no regex over HTML.

## OPSEC notes

- Residential proxy per worker; a datacenter ASN on this endpoint burns the proxy list fast.
- Keep attempt rate low and constant; bursts of auth.login from one IP trip the checkpoint
  heuristics regardless of credential validity.
- The endpoint's api_key is extractable from any current FB-family APK — treat it as public,
  but still harvest fresh per engagement.
