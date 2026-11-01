---
name: webhunter-os
category: bug-bounty
description: Web/API/cloud bug hunting operating system. 8-phase methodology + 5 knowledge bases (auth, injection, session, advanced patterns, exploit KB, playbooks, orchestrator) covering 172+ files. Use when auditing web apps, APIs, cloud infrastructure, OAuth/JWT, GraphQL, microservices, or any non-smart-contract target.
---

# WebHunter OS — Complete Web/API/Cloud Bug Hunting System

A 4-pillar operating system for systematic web security auditing, modeled after BugHunter OS but tailored for web/API/cloud targets.

## When to Use This Skill

Invoke when the user:
- Audits a web application (any tech stack)
- Tests API endpoints (REST, GraphQL, gRPC)
- Reviews cloud infrastructure (AWS, GCP, Azure)
- Hunts bugs in OAuth/JWT/SSO implementations
- Tests for IDOR, SSRF, SQLi, XSS, SSTI, RCE, deserialization
- Audits SPAs, microservices, modern web architectures
- Performs reconnaissance (subdomain, DNS, port scan, tech fingerprint)
- Reviews authentication & authorization
- Tests business logic flaws

## When NOT to Use

- Smart contract audits → use `bughunter-os` instead
- Pure mobile (iOS/Android native) → no dedicated skill yet
- General OSINT without web focus → use `soul.md` guidance

## System Architecture — 4 Pillars

### Pillar 1: 8-Phase Workflow
The `workflow/` directory contains the master 8-phase methodology:

| Phase | File | Purpose |
|---|---|---|
| 1 | `Phase1_Reconnaissance_Intelligence.md` | Passive & active recon: subdomain enum, DNS, port scan, tech fingerprint |
| 2 | `Phase2_Attack_Surface_Mapping.md` | Map every endpoint, parameter, API surface |
| 3 | `Phase3_Threat_Modeling.md` | Identify threats, trust boundaries, assets |
| 4 | (in `phase4-advanced/`) | Deep dive advanced patterns |
| 5 | (in `playbook-*`) | Per-vuln-class testing |
| 6 | `Phase6_Exploit_Validation_Impact.md` | Validate, measure impact, build PoC |
| 7 | (in `playbook-*`) | Business logic, chaining |
| 8 | `Phase8_Reporting_Remediation.md` | Final report, remediation advice |

### Pillar 2: Attack Pattern Library (42 patterns)
Reasoning-oriented patterns organized by category:

| Library | Files | Coverage |
|---|---|---|
| `phase1-auth` | 5 | IDOR, Broken Access Control, JWT, Broken Auth |
| `phase2-injection` | 6 | SQLi, SSTI, Command Injection, Mass Assignment |
| `phase3-session-api` | 9 | CORS, CSRF, GraphQL, REST API, session, file handling |
| `phase4-advanced` | 13 | WebSocket, Crypto, DoS, Business Logic, Misconfig, Info Disclosure |

### Pillar 3: Exploit Knowledge Base (44 cases)
How vulnerabilities manifest in the wild:

| Library | Files | Coverage |
|---|---|---|
| `exploit-kb-1` | 5 | SSRF, SQLi, IDOR, JWT token abuse |
| `exploit-kb-2` | 9 | CORS, CSRF, Path Traversal, RCE, etc |
| `exploit-kb-3` | 10 | Shadow API, Rate Limiting, Excessive Data Exposure, Mass Assignment |
| `exploit-kb-4` | 11 | Cloud: CI/CD, IAM, Nginx, Secrets Management |
| `exploit-kb-5` | 9 | Exploit chains, impact escalation, multi-step attacks |

Each file: Overview, Root Cause, Recon Signals, Validation Strategy, False Positive Guidance, Business Impact.

### Pillar 4: Protocol Playbooks (43 playbooks)
Operational workflows per vulnerability class:

| Library | Files | Coverage |
|---|---|---|
| `playbook-core` | 6 | API, Injection, Authz, Auth |
| `playbook-vuln` | 9 | RCE, Deserialization, Path Traversal, File Upload, etc |
| `playbook-modern` | 9 | SPA, Microservices, Event-Driven, API Gateway |
| `playbook-cloud` | 10 | IAM, Reverse Proxy, Secrets, CI/CD |
| `playbook-advanced` | 9 | AI Reasoning, Threat Modeling, Architecture Review, Reporting |

Each playbook: Objective, Preconditions, Workflow, Decision Points, Evidence Collection, Exit Criteria.

### Pillar 5: Orchestrator (44 files)
Adaptive workflow engine:

| Library | Files | Purpose |
|---|---|---|
| `orchestrator-core` | 8 | Workflow controller, report generator, finding correlator |
| `decision-engine` | 9 | Execution planner, confidence scoring, adaptive planner |
| `memory-state` | 9 | Knowledge cache, resume engine, context compression, checkpoint |
| `adaptive-reasoning` | 9 | Feedback loop, adaptive router, priority optimizer |
| `reporting-quality` | 9 | Assessment packager, remediation engine, quality gate |

## How to Use

### Starting a New Web Audit

1. **Phase 1 (Recon)**: Load `workflow/Phase1_Reconnaissance_Intelligence.md`
   - Subdomain enum, DNS analysis, port scan, tech fingerprint
2. **Phase 2 (Surface)**: Load `workflow/Phase2_Attack_Surface_Mapping.md`
   - Crawl, JS source map analysis, .git exposure, API discovery
3. **Phase 3 (Threat Model)**: Load `workflow/Phase3_Threat_Modeling.md`
   - Identify assets, trust boundaries, threats
4. **Phase 4 (Pattern Hunt)**: Reference `phase1-auth/`, `phase2-injection/`, etc
5. **Phase 5 (Deep Testing)**: Use playbooks for each vuln class
6. **Phase 6 (Exploit)**: Load `workflow/Phase6_Exploit_Validation_Impact.md`
7. **Phase 7 (Chain)**: Reference `exploit-kb-5/` for chaining techniques
8. **Phase 8 (Report)**: Load `workflow/Phase8_Reporting_Remediation.md`

### Looking Up a Specific Pattern

When user asks about a vulnerability class:

1. **Check `phase1-auth/` to `phase4-advanced/`** for pattern definitions
2. **Check `exploit-kb-1/` to `exploit-kb-5/`** for real-world manifestations
3. **Check `playbook-core/` to `playbook-advanced/`** for operational workflows
3. **Check `playbook-core/` to `playbook-advanced/`** for operational workflows
4. **Check `references/`** for session-derived condensed knowledge banks:
   - `references/api_audit_patterns_obol_session.md` for filter-ignoring search endpoints, NoSQLi via Express `qs`, auth-contract 500-vs-401 violations, and disambiguating bypass-vs-by-design.
   - `references/api_audit_patterns_circle_session.md` for GraphQL field-probing schema bypass on Apollo Server with introspection disabled, Next.js `_buildManifest.js` route-map dump, verbose-error API-key format leakage, 401/404 REST endpoint differential, and Cloudflare Lockout WAF coverage gaps (URL-encoded SQLi, NoSQLi operators in JSON args).
   - `references/api_audit_patterns_rolly_session.md` for no-KYC gambling business-logic audits — `?r=CODE` referral self-attribution race, user-chosen referral-code squatting with `^[a-zA-Z0-9_]+$` validation, daily-boost activation race on `pointsMining.activateWagerBoost`, VIP-gated game field `preRelease.targetAudience.vip`, the Gitbook `.md` export → formula-recon workflow, and the 8-question "open questions" socket-test table for any socket.io-driven casino bonus system.
   - `references/vdp_code_audit_patterns_nym_session.md` for broad VDP/open-source monorepo audits: policy-first safe testing, shared bearer-token agent/orchestrator trust boundaries, async credential retrieval ownership checks, auth-token logging triage, and untrusted `javascript:` link severity calibration.
   - `references/sap_occ_anonymous_cart_authz.md` for SAP Commerce OCC / Spartacus headless e-com: anonymous cart GUID capability-URL R/W IDOR, multi-baseSite dedupe, stealth-browser recon under Akamai, and triage notes (UUID entropy ≠ secure design).
   - `references/api_discovery_nosqli_express.md` for the 5-layer API discovery pipeline (robots.txt → JS → subdomain → Swagger → endpoint testing), NoSQL injection fingerprinting via error-response taxonomy, Express/NestJS fingerprinting, Sails.js dev-mode detection, CORS assessment pattern, marketplace/listing false-positive guard, and internal-service (bot-api/poh-api) risk assessment.

### Auditing a Specific Tech Stack

If user is testing:
- **REST API**: `playbook-core/API_Audit_Playbook.md` + `exploit-kb-3/`
- **GraphQL**: `phase3-session-api/GraphQL_Security.md` + `exploit-kb-3/`
- **OAuth/JWT**: `phase1-auth/JWT_Weaknesses.md` + `exploit-kb-1/`
- **Cloud (AWS/GCP/Azure)**: `exploit-kb-4/` + `playbook-cloud/`
- **Microservices**: `playbook-modern/Microservices_Playbook.md`
- **SPA**: `playbook-modern/SPA_Playbook.md`

## Common Attack Surfaces

### Authentication & Authorization
- IDOR / BOLA / BFLA
- Broken Authentication
- JWT weaknesses (alg confusion, kid injection, jku)
- OAuth/OIDC misconfigurations
- Session fixation
- MFA bypass

### Input Validation
- SQLi (Union, Boolean, Time, Error-based)
- SSTI (Jinja2, Twig, Freemarker, ERB)
- Command Injection
- XXE
- Mass Assignment

### Session & API
- CORS misconfig
- CSRF (modern protections bypass)
- GraphQL introspection
- REST API enumeration
- Rate limit bypass
- API key/secret leak

### Infrastructure
- SSRF (incl. cloud metadata 169.254.169.254)
- CORS misconfig
- Open redirects
- Subdomain takeover
- Cloud bucket misconfig (S3, GCS, Azure)
- CI/CD injection
- Secrets in git
- Terraform state leak

### Advanced
- WebSocket hijacking
- HTTP request smuggling
- Deserialization
- Race conditions
- Caching attacks
- Prototype pollution
- HTTP/2 attacks

## Key Principles

1. **Recon first, exploitation second** (Phase 1 must be thorough)
2. **Map all attack surface** (Phase 2) before testing
3. **Threat model before testing** (Phase 3) — know what to protect
4. **Check for false positives** — many "bugs" are intended behavior
5. **Chain vulnerabilities** — many critical bugs are combinations
6. **Document evidence** — screenshots, requests, responses
7. **Impact-driven reporting** — what can attacker actually do?

## File Structure (Total: 172 files)

```
webhunter-os/
├── SKILL.md (this file)
│
├── PILLAR 1: 8-Phase Workflow (8 files)
│   └── workflow/  (8 files: Phase1-Phase8)
│
├── PILLAR 2: Attack Pattern Library (33 files)
│   ├── phase1-auth/    (5 files)
│   ├── phase2-injection/    (6 files)
│   ├── phase3-session-api/    (9 files)
│   └── phase4-advanced/    (13 files)
│
├── PILLAR 3: Exploit Knowledge Base (44 files)
│   ├── exploit-kb-1/    (5 files)
│   ├── exploit-kb-2/    (9 files)
│   ├── exploit-kb-3/    (10 files)
│   ├── exploit-kb-4/    (11 files)
│   └── exploit-kb-5/    (9 files)
│
├── PILLAR 4: Protocol Playbooks (43 files)
│   ├── playbook-core/    (6 files)
│   ├── playbook-vuln/    (9 files)
│   ├── playbook-modern/    (9 files)
│   ├── playbook-cloud/    (10 files)
│   └── playbook-advanced/    (9 files)
│
└── PILLAR 5: Orchestrator (44 files)
    ├── orchestrator-core/    (8 files)
    ├── decision-engine/    (9 files)
    ├── memory-state/    (9 files)
    ├── adaptive-reasoning/    (9 files)
    └── reporting-quality/    (9 files)
```

## Usage Tips

- **Start with `workflow/Phase1_*`** for any new target
- **Cross-reference patterns + exploit KB** to recognize bugs
- **Use playbooks** for systematic testing per vuln class
- **Trust the orchestrator** for state management and quality
- **Combine with `bughunter-os`** for hybrid targets (smart contract + web frontend)
- **Combine with `soul.md`** for tactical execution (tools, scripts, real recon)

## Integration with Other Skills

| Skill | When to Combine |
|---|---|
| `bughunter-os` | DeFi protocol with web frontend |
| `soul.md` (bozagentic) | Always — operating philosophy + tooling |

## Update Policy

This skill is structured similar to `bughunter-os` for consistency. If new packs are added, install using same method (extract zip → copy to skill dir).
