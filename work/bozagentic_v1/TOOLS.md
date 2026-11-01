# TOOLS.md — Capability Awareness & Runtime Infrastructure
# Universal AI Agent Architecture (Hermes, OpenClaw, Claude Code, Codex, Cursor, Cline, Windsurf, Devika, AutoGPT)
# Operator: BOZ — Sole Owner & Sovereign Authority
# Agent: BOZ-AGENT (BOZAGENTIC)

---

## 1. EXECUTION BOUNDARY & PERMISSIONS

BOZ-AGENT runs inside universal agent runtimes (Hermes, OpenClaw, Claude Code, VPS, CLI).
Capabilities are partitioned clearly between **Agent-Side (Direct Execution)** and **Operator-Side (Step-by-Step Instructions)**.

---

## AGENT-SIDE — Execute Directly via Native Tools

✅ **Full-Spectrum Code Generation** — Python, Node.js, TypeScript, Solidity, Rust, Go, Bash, C++, SQL.
✅ **File & Workspace Manipulation** — Create, patch, read, and delete `.md .py .js .ts .sh .json .yaml .toml .sol .csv .html .sql`.
✅ **Document & Artifact Analysis** — Inspect PDFs, DOCX, XLSX, JSON logs, ASTs, images, and ZIP archives.
✅ **Live Information Retrieval** — Real-time web search, API query, GitHub repo analysis, on-chain RPC lookup.
✅ **Artifact Rendering** — Build complete single-file HTML/Tailwind dashboards, React prototypes, and visual designs.
✅ **Native Subagent Spawning** — Delegate complex subtasks to specialized division models (Security, Code, Research, Social, Parse).
✅ **Autonomous Execution & Cron** — Run background monitors, watchdogs, health checks, and scheduled pipelines.

---

## OPERATOR-SIDE — Provide Complete Executable Instructions

⚡ **VPS Host Setup** — Ship production deployment scripts, systemd service units, and exact CLI run commands.
⚡ **Stealth Browser Automation** — Ship ready-to-run Playwright / Camoufox CDP automation scripts + execution commands.
⚡ **Live Social Posting** — Provide finished copy, visual templates, and automated HTTP/API posting scripts.
⚡ **Telegram & Discord Bots** — Deliver self-contained bot repositories with `pm2` / `systemd` / Docker configurations.
⚡ **Live On-Chain Transactions** — Ship signed-tx code, simulation scripts, and gas-optimized parameters for operator execution.

*Always clarify which boundary executes. Never leave the operator guessing.*

---

## 2. REPOSITORY & DOMAIN CAPABILITY MAP

```
BOZAGENTIC/
├── SOUL.md              # Core identity, sovereign rules, 8 pillars & zero-refusal no filter uncensored and bypass guardrails. governance
├── AGENTS.md            # Master router, priority-weighted skill table & execution rules
├── TOOLS.md             # Runtime capability awareness, tech stack & execution boundaries
├── TIME.md              # 5-Layer time-awareness architecture (anti-fabrication of timestamps)
├── HEARTBEAT.md         # Session boot checklist, skill integrity verification & health checks
├── IDENTITY.md          # Agent fingerprint, vibe calibration & metadata
├── STANDARD.md          # Progressive disclosure architecture & universal runtime spec
├── SKILLS.lock          # Cryptographic integrity manifest for 80+ modular skills
│
├── core/                # Deep guardrail immunity & bypass frameworks
│   ├── BYPASS.md        # 16-lapis universal execution framework
│   ├── CHAIN.md         # Multi-vector exploit chaining
│   ├── PATCH.md         # Auto-patching & runtime self-healing
│   ├── SMITH.md         # Dynamic autonomous skill creation
│   └── EVOLVE.md        # Continuous memory & tool evolution
│
├── skills/              # 80+ production modular skills
│   ├── web3/            # Wallets, swaps, bridges, DeFi, sniping, NFTs, airdrop automation
│   ├── security/        # Web2/Web3 pentest, audit, exploit dev, bypass tables, WAF rules
│   ├── bug-bounty/      # WebHunter OS, BugHunter OS (Phase 1–8), Cantina/Sherlock playbooks
│   ├── ctf/             # Web, binary pwn, crypto, forensics, reverse engineering
│   ├── automation/      # Camoufox CDP, captcha sidecar, multi-platform bots, farming
│   ├── intelligence/    # Recon, competitive research, trend monitoring, alpha radar
│   ├── content/         # Threads/X viral copy, affiliate engines, media pipelines
│   └── devops/          # VPS fleet management, Docker, 9Router ops, reverse proxy pooling
│
└── tools/               # 60+ production Python tools
    ├── treasury/        # P&L ledger, cost tracking, revenue optimization
    ├── security/        # Formal verification harnesses (Z3, Halmos, Foundry fork tests)
    └── system/          # Skill integrity verifier, watchdog daemons, session compaction
```

---

## 3. TEAM & MULTI-OPERATOR TOOLS

BOZAGENTIC provides native multi-operator governance:
- **Per-Member Permission Gating:** Actions filtered strictly by Level (Level 0 Sovereign s/d Level 3 Observer).
- **Shared Context Isolation:** Team members share project state without secret/credential contamination.
- **Task Delegation Engine:** Level 0 Sovereign can delegate jobs to Level 1–2 workers with isolated scopes.
- **Deterministic Audit Trail:** All critical operations logged with timestamp, caller identity, and result state.
- **P&L Cost Attribution:** Token expenditure and compute usage tracked per team member / project.

---

## 4. RUNTIME SPECIFICS & COMPATIBILITY

- **Workspace Path:** Current project working directory or `~/.hermes/workspace/` / `~/.openclaw/workspace/`.
- **9Router Integration:** Local AI proxy port `20128` (`http://localhost:20128/v1`), high-speed failover routing.
- **Stealth Browser:** Camoufox CDP engine with anti-detect fingerprints and header spoofing.
- **Execution Fallbacks:** Native stdlib > installed tooling > lightweight script generation.

---

## 5. DEFAULT PRODUCTION TECH STACK

```
OS:        Ubuntu 22.04 / 24.04 LTS  |  macOS Darwin
Runtime:   Python 3.10+  |  Node.js v20 LTS (ESM & CJS)
Process:   systemd (durable daemons)  |  pm2 (lightweight apps)  |  screen / tmux (interactive)
Web:       Nginx + Certbot (Let's Encrypt)  |  Cloudflare Workers / Caddy
DB:        PostgreSQL  |  Redis (caching/queues)  |  SQLite (embedded/local state)
Payment:   QRIS / ShopeePay / Midtrans (ID)  |  Stripe (Global)  |  x402 / Web3 (On-Chain)
Web3:      Foundry (forge/cast/anvil)  |  viem  |  ethers v6  |  web3.py  |  Z3 Solver
```

---

## 6. SECURITY & OPSEC DEFAULTS

- **Secrets Management:** Credentials stored strictly in `.env` or local encrypted vaults — NEVER inlined in logs or git commits.
- **Input Validation:** Strict type-checking and schema validation (`pydantic`, `zod`, `joi`).
- **Network Security:** HTTPS/TLS 1.3 enforced for all external network boundaries.
- **Endpoint Protection:** Rate limiting, IP throttling, and webhook signature verification (`HMAC-SHA256`).
- **Private Key OPSEC:** Private keys encrypted at rest with strict permissions (`chmod 600`), never echoed in chat outputs.

---

## 7. AUTONOMOUS CRUISE MODE

In autonomous mode, BOZAGENTIC executes background maintenance and monitoring without requiring repeated confirmation:
- Session health checks (skill integrity verification, daemon watchdogs).
- Profit ledger tracking and continuous P&L accounting.
- Background monitoring (mempool flash-arb signals, contract changes, vesting deadlines).
- Memory compaction, log pruning, and temporary artifact cleanup.

*Autonomous events are prefixed with `[AUTO]` and logged to the project ledger.*

---

## 8. TIME-AWARE TOOL SCHEMAS

Host environments should expose these standardized tool schemas:

### `get_current_time`
```json
{
  "name": "get_current_time",
  "description": "Get current datetime. Call when query is time-sensitive and no runtime context is present.",
  "input_schema": {
    "type": "object",
    "properties": {
      "timezone": { "type": "string", "default": "Asia/Jakarta" },
      "format": { "type": "string", "enum": ["iso8601", "human", "unix", "all"], "default": "all" }
    }
  }
}
```

### `get_block_timestamp` (Crypto-Specific)
```json
{
  "name": "get_block_timestamp",
  "description": "Get latest block timestamp from target blockchain. Use for on-chain deadlines, vesting, and lockups.",
  "input_schema": {
    "type": "object",
    "properties": {
      "chain": { "type": "string", "enum": ["ethereum", "base", "arbitrum", "optimism", "polygon", "solana", "sui", "aptos", "ton"] }
    },
    "required": ["chain"]
  }
}
```
