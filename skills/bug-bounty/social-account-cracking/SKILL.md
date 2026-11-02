---
name: social-account-cracking
description: 'Build/patch social mobile-API credential testing tools.'
---

# SOCIAL ACCOUNT CREDENTIAL TESTING (MOBILE APIS)

Class-level skill for the operator's own account-testing tooling: scripts that test credentials
against a social platform's **mobile app API** rather than its web login. Facebook's `b-api`
`auth.login` endpoint is the reference implementation (see references/facebook-bapi-auth.md).

> Not bug-bounty password spray. If the task is "spray a wordlist against one login endpoint for
> a BB program", that is the `credential-attack` skill instead. This skill is for building and
> maintaining platform-API credential testers.

---

## ALWAYS-ON RULES

1. **Patch in place, never rewrite.** Existing tools (ESBF-style crackers) have working
   threading, proxy rotation, and output handling. Swap only the request method; a full rewrite
   re-introduces bugs the original already fixed.
2. **Deliver the final artifact as a file** (MEDIA attachment), complete and runnable — no
   "here's the snippet, assemble it yourself". The operator pastes and runs.
3. **Run the whole chain before reporting it as verified.** Writing a patcher is not running it:
   copy original -> patch -> compile -> execute the greps/checks that prove the patch landed, and
   only then say "verified". A claimed verification without real execution is a false report.
4. **Never carry credential material in notes.** API keys/tokens harvested from transcripts are
   versioned and rotatable — record the source (which APK field), never the value.

---

## PROCEDURE

### 1. Harvest the API contract from a CURRENT APK

The mobile API contract is versioned and the web one drifts. Before writing any request:

- Decompile a recent APK (`apktool d app.apk`) and grep for the endpoint + api_key:
  `grep -rn "auth.login\|api_key" target_src/`
- Capture the exact request shape with the proxy chain (see the mobile-pentest skill): params,
  `format=json`, `generate_session_cookies`, `locale`, and the api_key version string.
- **api_key values are versioned.** Harvest from the current APK, never from old notes.

### 2. Classify responses — the test loop depends on it

Facebook b-api classification (full table in references/facebook-bapi-auth.md):

```
"error_msg" == "Invalid username or password"  -> bad creds, continue
error.code == 405 / "Invalid parameters"        -> request shape wrong, FIX, don't spin
two_factor / checkpoints                       -> live account needing 2FA/checkpoint -> checkpoint bucket
cookies + access_token present                 -> success -> session bucket
```

Persist outcomes to separate buckets (ok/cp/2fa) and never let a classification crash abort the
run — wrap the classifier, log the raw response on the unknown branch.

### 3. Session + machine-id reuse

- `generate_session_cookies=1` returns cookies that replay against `b-api.facebook.com` — reuse
  the session instead of re-login for follow-up actions.
- `machine_id` must be stable per target (UUIDv4 generated once, then reused); rotating it
  mid-run looks like a new device and invites checkpoint challenges.
- Send `Authorization: OAuth <token>` only when a step requires it; harvest from the app's
  stored prefs at runtime rather than hardcoding.

### 4. Proxy rotation + threading model

- Rotate residential proxies per worker (`.prox.txt` file, one `ip:port` per line) with PySocks.
- Keep worker count conservative for the box (small VPS: ~25 threads, streaming flush per
  result — a shared counter mutated across threads without a lock silently loses counts).
- Every network call gets a timeout; a hung connection without one stalls a worker forever.

### 5. Build the patcher as a chainable, fail-loud script

When swapping a tool's method (e.g. GraphQL -> b-api), write a patcher that:

- Uses `re.subn` and **asserts the expected replacement count**, exiting 1 on mismatch (fail
  loud, not silent no-op).
- Runs `py_compile` on the output before delivering.
- Keeps the original untouched: `cp original.py patched.py` first.

> **re.sub backslash pitfall:** the replacement string is a regex template — every literal
> backslash in generated code must be doubled in the patcher (write `\xNN` into the target file
> by putting `\\xNN` in the replacement). A single-pass escape (`'\x%02x'` emitted as `'\x%02x'`)
> produces broken source that only fails at runtime.

---

## VERIFY BEFORE CLAIMING DONE

```bash
cp original.py patched.py
python3 patcher.py patched.py        # must exit 0 with expected counts
python3 -m py_compile patched.py     # must exit 0
grep -n "auth.login\|api_key" patched.py   # prove the swap landed
```

Only after this chain passes, deliver the file. If the chain fails, report the actual failure
line — never "verified".

---

## RELATED

- `mobile-pentest` — the APK decompile, proxy, and SSL-pinning pipeline that harvests the API
  contract in step 1.
- `credential-attack` — bug-bounty password spray (different class, different skill).
