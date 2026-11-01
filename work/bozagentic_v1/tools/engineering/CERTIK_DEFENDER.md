# CERTIK + OPENZEPPELIN DEFENDER — MASTER REFERENCE
# Audit Methodology · Monitoring · Incident Response · Automation
# BOZAGENTIC · 2026-07-29

---

## 1. CERTIK

### 1.1 What CertiK Is

CertiK = blockchain security firm. 3 produk utama:

```
1. AUDIT       — Smart contract security audit (manual + automated)
2. SKYNET      — Real-time monitoring & alerting (24/7)
3. SCANNER     — Automated vulnerability scanner (self-serve)
```

### 1.2 CertiK Audit Methodology

**Phases:**
```
Phase 1: Scoping
  - Define audit scope (contracts, LOC, complexity)
  - Identify critical paths (fund flows, admin functions)
  - Agree on timeline (1-4 weeks typical)

Phase 2: Automated Analysis
  - Static analysis (Slither, custom tools)
  - Fuzzing (Echidna, custom fuzzer)
  - Symbolic execution (Mythril, Manticore)
  - Formal verification (CertiK proprietary: FP — Formal Proof engine)

Phase 3: Manual Review
  - 2 auditors minimum per project
  - Line-by-line review of critical functions
  - Business logic verification
  - Cross-contract interaction analysis
  - Economic attack modeling

Phase 4: Report
  - Findings classified: CRITICAL / MAJOR / MINOR / INFORMATIONAL
  - Each finding: description, impact, PoC, recommendation
  - Client fixes → re-review → final report

Phase 5: Certification
  - CertiK badge/score (0-100)
  - Published on certik.com/projects
  - Ongoing monitoring via Skynet
```

### 1.3 CertiK Finding Classification

| Severity | Criteria | Example |
|----------|----------|---------|
| **CRITICAL** | Direct fund loss, no user interaction | Reentrancy draining vault |
| **MAJOR** | Fund loss with conditions, or protocol halt | Oracle manipulation |
| **MINOR** | Limited impact, edge case | Front-running opportunity |
| **INFORMATIONAL** | Best practice, gas optimization | Missing event emission |

### 1.4 CertiK Formal Verification (FP Engine)

```
CertiK's proprietary formal verification:
  - Converts Solidity → intermediate representation
  - Generates mathematical specifications
  - Proves properties via SMT solvers (Z3, CVC5)
  - Covers: overflow, access control, state invariants

Similar to: Halmos (open-source), Certora (commercial)
Difference: CertiK integrates with their audit workflow
```

### 1.5 CertiK Skynet (Monitoring)

```
Real-time on-chain monitoring:
  - Transaction pattern analysis
  - Abnormal fund flow detection
  - Governance attack detection
  - Oracle manipulation alerts
  - Liquidity drain detection
  - Contract upgrade monitoring

Alert channels: webhook, email, Telegram, PagerDuty
Response time: < 1 minute for critical alerts
```

### 1.6 CertiK Scanner (Self-Serve)

```
Automated scanning (no manual review):
  - Upload contract → get report in minutes
  - Checks: reentrancy, overflow, access control, etc.
  - Score: 0-100 (security score)
  - NOT a substitute for full audit
  - Good for: quick pre-audit check, CI/CD integration

Similar to: Slither + custom rules + scoring
```

### 1.7 CertiK Audit Report Structure

```
1. Executive Summary
   - Scope, timeline, team
   - Overall assessment
   - Score

2. Findings Summary
   - Table: ID, Severity, Status (Fixed/Acknowledged/Won't Fix)

3. Detailed Findings
   For each:
   - Title
   - Severity
   - Description
   - Impact
   - Proof of Concept (code)
   - Recommendation
   - Fix verification

4. Appendix
   - Files reviewed
   - Tools used
   - Methodology
   - Disclaimer
```

### 1.8 How to Read a CertiK Report (for Bug Bounty)

```
1. Check SCOPE — is your target contract in scope?
2. Check FINDINGS — what did they find? What did they MISS?
3. Check "Won't Fix" / "Acknowledged" — accepted risks = potential targets
4. Check APPENDIX — tools used = what they DIDN'T check manually
5. Cross-reference with on-chain state — is the deployed code the audited version?

Common misses by CertiK (and most auditors):
  - Cross-contract composability attacks
  - Economic/oracle manipulation
  - Governance attack vectors
  - Flash loan + governance combo
  - Front-running / MEV exploitation
  - Upgrade-related storage collisions
```

### 1.9 CertiK vs Other Audit Firms

| Firm | Strength | Weakness |
|------|----------|----------|
| **CertiK** | Scale, formal verification, monitoring | Volume > depth (many audits) |
| **Trail of Bits** | Deep technical, tool development | Expensive, slow |
| **OpenZeppelin** | Standard author, deep understanding | Limited availability |
| **Cyfrin** | DeFi focused, Patrick Collins | Newer firm |
| **Halborn** | Broad coverage | Variable quality |
| **Spearbit** | Senior auditors, portfolio model | Small capacity |
| **Code4rena** | Competitive audit (many eyes) | Inconsistent depth |
| **Immunefi** | Bug bounty platform (not auditor) | Depends on hunters |

### 1.10 CertiK for Bug Hunters

```
Strategy:
1. Find protocols with CertiK audit badge
2. Read the audit report (public on certik.com)
3. Look for:
   - "Acknowledged" findings (protocol accepted risk)
   - Findings marked "Fixed" → verify fix is actually deployed
   - Scope limitations → contracts NOT audited
   - Post-audit changes → code changed after audit
4. Focus on what auditors MISS:
   - Composability (protocol + external DeFi)
   - Economic attacks (flash loan + oracle)
   - Governance manipulation
   - Cross-chain replay
```

---

## 2. OPENZEPPELIN DEFENDER

### 2.1 What OZ Defender Is

```
OZ Defender = security operations platform for smart contracts.
NOT an audit tool. It's RUNTIME security:
  - Monitor contracts in production
  - Automate responses to incidents
  - Manage upgrades safely
  - Enforce transaction policies
  - Multi-sig coordination
```

### 2.2 Defender Components

```
┌─────────────────────────────────────────────────────┐
│                  OZ DEFENDER                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📡 MONITOR     — Real-time event/tx monitoring     │
│  🤖 AUTOTASK    — Serverless functions (Lambda-like)│
│  📋 SENTINEL    — Alert rules + triggers            │
│  🔄 RELAYER     — Meta-transaction relay            │
│  🏛 ADMIN       — Upgrade management (UUPS/Transp)  │
│  🔐 SAFE        — Multi-sig coordination            │
│  📊 INSPECTOR   — Contract inspection dashboard     │
│  🔗 ACTIONS     — On-chain action automation        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.3 Monitor

```
What it watches:
  - Contract events (Transfer, Approval, OwnershipTransferred, etc.)
  - Transaction patterns (large transfers, unusual callers)
  - State changes (storage slot modifications)
  - Contract upgrades (implementation changes)
  - Balance changes (ETH, ERC20)

Alert conditions:
  - Event emitted with specific parameters
  - Transaction value > threshold
  - Function called by non-owner
  - Storage slot changed
  - Contract selfdestructed
  - Proxy implementation changed

Notification channels:
  - Email, Slack, Discord, Telegram, PagerDuty, Webhook
```

### 2.4 Sentinel (Alert Rules)

```yaml
# Example Sentinel configuration
name: "Large Transfer Alert"
type: FORTA  # or BLOCK, EVENT, TXPOOL
conditions:
  - event: "Transfer(address,address,uint256)"
    condition: "amount > 1000000e6"  # > $1M USDC
  - addresses:
      - "0xYourVault"
notification:
  - type: webhook
    url: "https://your-incident-response.com/alert"
  - type: telegram
    chat_id: "-100xxx"
autotask: "auto-pause-on-large-transfer"
```

### 2.5 Autotask (Serverless Functions)

```javascript
// Autotask: Auto-pause contract on suspicious activity
const { Defender } = require('@openzeppelin/defender-sdk');
const { ethers } = require('ethers');

exports.handler = async function(event) {
  const client = new Defender(event);
  const signer = await client.getSigner();

  const vault = new ethers.Contract(
    process.env.VAULT_ADDRESS,
    ['function pause() external'],
    signer
  );

  // Check if alert is legitimate
  const { matchReasons, transaction } = event.request.body;

  if (matchReasons.some(m => m.condition === 'large_transfer')) {
    console.log('Large transfer detected, pausing vault...');
    const tx = await vault.pause();
    await tx.wait();
    console.log(`Vault paused. TX: ${tx.hash}`);
  }

  return { paused: true, txHash: tx.hash };
};
```

**Autotask triggers:**
- Sentinel alert fired
- Schedule (cron-like)
- Webhook (external trigger)
- Monitor event

### 2.6 Relayer (Meta-Transactions)

```
What: Execute transactions on behalf of users (gasless UX)

Architecture:
  User signs message (off-chain)
    → Relayer picks up
    → Relayer submits tx (pays gas)
    → Contract verifies signature
    → Execution happens

OZ Defender Relayer:
  - Managed key infrastructure (HSM-backed)
  - Multi-chain support
  - Policy enforcement (speed limits, allowlists)
  - Nonce management
  - Gas price optimization

Use cases:
  - Gasless token transfers (ERC-2771)
  - Meta-transaction forwarding
  - Automated contract interactions
  - Emergency pause execution
```

### 2.7 Admin (Upgrade Management)

```
What: Safely manage proxy upgrades

Features:
  - Propose upgrade (new implementation)
  - Multi-sig approval workflow
  - Storage layout compatibility check
  - Upgrade simulation (fork + test)
  - Execution with timelock
  - Rollback capability

Workflow:
  1. Developer proposes new implementation
  2. Defender checks storage layout compatibility
  3. Simulation on fork (run tests against new impl)
  4. Multi-sig approval (Gnosis Safe integration)
  5. Timelock delay (24-72h typical)
  6. Execution (upgradeToAndCall)
  7. Post-upgrade verification

Supports:
  - Transparent proxy (ProxyAdmin)
  - UUPS proxy
  - Beacon proxy
  - Custom proxy patterns
```

### 2.8 Actions (On-Chain Automation)

```
Pre-built actions:
  - Pause/unpause contract
  - Transfer ownership
  - Grant/revoke roles
  - Execute governance proposal
  - Withdraw from timelock
  - Upgrade implementation

Custom actions:
  - Any ABI-encoded function call
  - Conditional execution
  - Multi-step workflows
  - Cross-chain coordination
```

### 2.9 Defender SDK (Node.js)

```javascript
// Install: npm install @openzeppelin/defender-sdk

// Monitor
const { MonitorClient } = require('@openzeppelin/defender-sdk-monitor-client');
const monitor = new MonitorClient({ apiKey, apiSecret });
await monitor.createNotificationChannel({ type: 'webhook', ... });

// Autotask
const { AutotaskClient } = require('@openzeppelin/defender-sdk-autotask-client');
const autotask = new AutotaskClient({ apiKey, apiSecret });
await autotask.create({ name: 'my-autotask', code: '...' });

// Relayer
const { Relayer } = require('@openzeppelin/defender-sdk-relayer');
const relayer = new Relayer({ apiKey, apiSecret });
const signer = await relayer.getSigner();

// Admin (upgrades)
const { AdminClient } = require('@openzeppelin/defender-sdk-admin-client');
const admin = new AdminClient({ apiKey, apiSecret });
await admin.createUpgradeProposal({ ... });

// Actions
const { ActionsClient } = require('@openzeppelin/defender-sdk-actions-client');
```

### 2.10 Defender for Incident Response

```
INCIDENT PLAYBOOK (using Defender):

T+0: Alert fires (Sentinel detects anomaly)
  → "Large transferFrom on Vault: $5M USDC"

T+1min: Autotask executes
  → Auto-pause contract
  → Notify team (Telegram + PagerDuty)

T+5min: Team assesses
  → Check: is this legitimate? (governance vote? exploit?)
  → If exploit: keep paused, investigate
  → If false positive: unpause

T+30min: Investigation
  → Trace fund flow (Etherscan, Tenderly)
  → Identify attacker address
  → Check if ongoing

T+1h: Response
  → If exploit: blacklist attacker, revoke approvals
  → If governance: verify proposal legitimacy
  → Communicate to community

T+24h: Recovery
  → Fix vulnerability (if exploit)
  → Deploy fix via Admin (upgrade with timelock)
  → Unpause
  → Post-mortem
```

### 2.11 Defender Configuration Examples

**Emergency Pause System:**
```
Sentinel: watch for "drain pattern" (multiple transferFrom in 1 block)
  → Autotask: call pause() on contract
  → Autotask: send alert to team Telegram
  → Autotask: revoke all approvals from suspicious spender

Upgrade Safety:
  Admin: propose upgrade
  → Storage layout check (automatic)
  → Fork simulation (run test suite)
  → Multi-sig approval (3/5 signers)
  → 24h timelock
  → Execute

Large Transfer Monitor:
  Sentinel: Transfer event > $100k
  → Alert to Telegram
  → Log to dashboard
  → If > $1M: auto-pause + page on-call
```

### 2.12 Defender vs Alternatives

| Feature | OZ Defender | Forta | Tenderly | Custom |
|---------|-------------|-------|----------|--------|
| Monitoring | ✅ | ✅ | ✅ | Build yourself |
| Auto-response | ✅ (Autotask) | ✅ (bots) | ⚠️ (alerts only) | Build yourself |
| Upgrade mgmt | ✅ (Admin) | ❌ | ❌ | Build yourself |
| Relayer | ✅ | ❌ | ❌ | Build yourself |
| Multi-sig | ✅ (Safe) | ❌ | ❌ | Gnosis Safe |
| Cost | $$$ (SaaS) | Free (decentralized) | $$ | Free (your time) |
| Setup | Minutes | Hours | Minutes | Days-weeks |

### 2.13 Defender for Bug Bounty / Audit

```
How defenders protect protocols (what you're trying to bypass):

1. MONITORING — they'll see your exploit tx in mempool or next block
   → Bypass: flash loan (atomic, 1 block, no time to react)
   → Bypass: MEV bundle (private mempool, no front-running)

2. AUTO-PAUSE — contract pauses on suspicious activity
   → Bypass: exploit in 1 tx (pause can't stop atomic attack)
   → Bypass: governance attack (pause requires owner, you become owner)

3. UPGRADE TIMELOCK — can't instantly fix
   → Bypass: exploit during timelock window (24-72h)
   → Bypass: exploit the upgrade itself (storage collision)

4. MULTI-SIG — admin actions need multiple signers
   → Bypass: social engineering (phish signers)
   → Bypass: find function that doesn't need multi-sig

5. RELAYER POLICIES — rate limits, allowlists
   → Bypass: direct contract call (bypass relayer)
   → Bypass: find unprotected function
```

---

## 3. COMBINED AUDIT PIPELINE (FULL STACK)

### 3.1 Pre-Audit (Automated)

```bash
# Step 1: Slither (static, seconds)
slither src/ --json slither.json

# Step 2: Mythril (symbolic exec, minutes)
python3 -m mythril analyze src/Critical.sol --execution-timeout 300

# Step 3: Halmos (formal proof, seconds-minutes)
halmos --contract ProtocolTest --solver z3

# Step 4: Echidna (fuzz, minutes-hours)
echidna src/ --contract Fuzz --test-limit 100000

# Step 5: Foundry fuzz (regression)
forge test --fuzz-runs 10000
```

### 3.2 Manual Audit (Human)

```
1. Read docs → understand invariants
2. Read code → line-by-line critical paths
3. Model attacks → flash loan, oracle, governance, reentrancy
4. Write PoC → Foundry test proving exploit
5. Classify → CRITICAL / MAJOR / MINOR / INFO
6. Report → description, impact, PoC, fix
```

### 3.3 Post-Deploy (Runtime)

```
1. OZ Defender Monitor → watch events, tx patterns
2. CertiK Skynet → 24/7 monitoring (if subscribed)
3. Sentinel alerts → auto-pause on anomaly
4. Autotask → automated incident response
5. Admin → safe upgrade management
6. Bug bounty → Immunefi listing for ongoing discovery
```

### 3.4 Full Security Lifecycle

```
DESIGN → AUDIT → DEPLOY → MONITOR → RESPOND → UPGRADE → RE-AUDIT
  │         │        │         │          │         │          │
  │    Slither    Defender  Sentinel  Autotask   Admin    CertiK
  │    Mythril    Monitor   Alerts    Pause     Timelock  OZ
  │    Halmos     Relayer   Webhook   Blacklist Multi-sig  Re-scan
  │    Echidna    Policies  Telegram  Revoke    Storage
  │    Manual     Safe      PagerDuty Trace     Sim
  │    CertiK
  │    OZ Audit
```

---

## 4. KEY TAKEAWAYS FOR BUG HUNTING

### What CertiK/OZ audits typically MISS:

```
1. COMPOSABILITY — protocol + external DeFi interaction
   (Auditors check protocol in isolation)

2. ECONOMIC ATTACKS — flash loan + oracle + governance combo
   (Requires understanding market dynamics)

3. POST-AUDIT CHANGES — code deployed ≠ code audited
   (Check: implementation address matches audit scope?)

4. CROSS-CHAIN — same contract, different chain, different context
   (Replay attacks, different oracle sources)

5. GOVERNANCE — proposal manipulation, vote buying
   (Auditors focus on code, not governance mechanics)

6. UPGRADE PATHS — storage collision, uninitialized proxy
   (Auditors check current code, not future upgrades)

7. MEV/FRONT-RUNNING — transaction ordering exploitation
   (Auditors assume fair ordering)
```

### Your edge as bug hunter:

```
CertiK: 100+ audits/year, 2 weeks each → depth limited
You:     1 protocol, unlimited time → depth unlimited

CertiK: automated tools + manual review
You:     automated tools + creative attack modeling

CertiK: checks what's IN scope
You:     checks what's OUT of scope + interactions

CertiK: reports bugs
You:     reports bugs + gets paid (Immunefi)
```

---

*OZ Defender: SaaS platform (defender.openzeppelin.com), Node.js SDK*
*CertiK: Audit firm + Skynet monitoring + Scanner*
*Neither is installable as a local tool — both are services*
*But their METHODOLOGY is what matters for your audit workflow*
*BOZAGENTIC · "Know their playbook. Find what they missed."*
