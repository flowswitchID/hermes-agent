# VDP/BBP code-audit patterns from Nym session

Use this reference when a program has a broad VDP page rather than a platform-scoped asset list, and the target is an open-source monorepo with Rust/TypeScript services.

## Policy-first workflow
- Capture safe-testing rules before any probing: no DoS, no touching other users' data, production testing only with own account, social engineering/DDoS/physical out of scope.
- Prefer local code audit and local reproduction for broad VDPs; avoid live scanning unless the policy explicitly permits it.
- Record eligible/ineligible classes verbatim, then classify each candidate against that policy before writing a report.

## Candidate triage lessons
- Shared bearer-token systems are not automatically auth bypasses. Treat them as cross-principal privilege issues only if one token holder can affect other agents/users or forge data outside its assigned authority.
- For agent/orchestrator systems, check whether work assignments bind to an agent identity. Red flags: assignment tables that store only `node_id`/`started_at`, submit endpoints that accept only `node_id + result`, and handlers that authenticate only a shared token.
- For async credential/issuance APIs, distinguish service-wide bearer auth from per-user ownership. If a `secret` is only sent in webhook payloads but retrieval endpoints use predictable `id` or `(device_id, credential_id)` without the secret, validate who can access the bearer token before claiming cross-user disclosure.
- Logging auth tokens is a sensitive-leak smell (`debug!("header value: ...")`, `debug!("parsed token: ...")`), but usually needs production debug logging or log-reader access to be bounty-grade.
- `javascript:` links from untrusted API data are real XSS sinks, but often weak if click-required and attacker control of the upstream data is hard. Frame as stored/click XSS only when the upstream data is in-scope and attacker-controllable.

## Evidence checklist for report-grade findings
- At least one LoC for authorization decision and one LoC for state mutation/effect.
- Preconditions: who has the token/key/role; whether that principal is trusted or merely one of many semi-trusted clients/agents.
- Impact: concrete privacy/data/integrity effect, not just "can call endpoint".
- Local PoC preferred: start service with known token, seed local DB/fixture, submit forged request, read back changed state.
