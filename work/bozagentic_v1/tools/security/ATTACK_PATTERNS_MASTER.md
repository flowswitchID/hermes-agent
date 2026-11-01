# SOLODIT + QUANTSTAMP ATTACK PATTERNS
# Vulnerability Database + Monthly Incident Analysis
# BOZAGENTIC · 2026-07-30

---

## 1. SOLODIT (Cyfrin's Vulnerability Database)

### What it is:
```
URL:        solodit.xyz
Size:       52,697 findings (and growing)
Source:     ALL audit firms (Code4rena, Sherlock, Cantina, etc.)
Format:     Searchable by severity, protocol, language, category
Access:     Free (signup required for full access)
```

### How to use for auditing:
```
BEFORE auditing a protocol:
  1. Search Solodit for protocol TYPE (lending, DEX, bridge, etc.)
  2. Filter by HIGH severity
  3. Read top 20 findings for that category
  4. Build checklist of "known bugs for this protocol type"
  5. Check each one against target code

DURING auditing:
  1. Found something suspicious?
  2. Search Solodit for similar pattern
  3. Check if it's been reported before (duplicate risk)
  4. Read how it was fixed in other protocols

AFTER auditing:
  1. Compare findings against Solodit patterns
  2. Did you miss any known patterns?
  3. Update your personal checklist
```

### Recent Findings from Solodit (July 2026):
```
Jupiter Lend (Code4rena contest):
  M-01: Broken safety cap in liquidate.rs → permanent DoS during crashes
  M-02: Interest-bearing suppliers over-credited → reserve deficit
  M-03: get_supply_ratio() compares raw shares to normal tokens → insolvency

  → All 3 are ACCOUNTING ERRORS in lending protocol
  → Pattern: interest-bearing vs non-interest-bearing share confusion
  → Lesson: ALWAYS check share/token conversion with interest accrual

Shieldify Security (Jul 22, 2026):
  M-01: Permissionless poke() zeros out veNFT bribes/fees
  M-02: Invalidating locked report → uncapped emission release
  M-03: Gauge-cap enforcement bypassed via permissionless updateFor
  L-01: Provenance fields silently rewritten on locked reports
  L-02: expiredIndexFloor strands gauge emission share
  L-03: governanceCapActive disables emergencyCouncil circuit breaker

  → Pattern: PERMISSIONLESS functions with unintended side effects
  → Pattern: Circuit breaker bypass via state interaction
  → Lesson: Check ALL permissionless functions for state side effects
```

### Top Vulnerability Categories (from 52K findings):
```
1. ACCESS CONTROL (most common HIGH)
   → Missing onlyOwner/onlyRole
   → Permissionless functions with admin effects
   → Role escalation via state manipulation

2. ACCOUNTING ERRORS (most common MEDIUM)
   → Share/token conversion with interest
   → Rounding direction inconsistency
   → Fee calculation errors
   → Double-counting (balance + internal accounting)

3. STATE MACHINE ERRORS
   → State not cleared on lifecycle transitions
   → Stale data after reconnect/upgrade
   → Race conditions in multi-step operations

4. ORACLE MANIPULATION
   → Spot price without TWAP
   → Stale price checks missing
   → Flash loan price manipulation

5. REENTRANCY
   → State change after external call
   → Cross-function reentrancy
   → ERC721/ERC777 callback reentrancy

6. ECONOMIC EXPLOITS
   → Inflation attack (ERC4626 first depositor)
   → Donation attack (balanceOf accounting)
   → Governance attack (flash loan voting)
   → Liquidation manipulation
```

---

## 2. QUANTSTAMP SECURITY BEAT (Monthly Incident Reports)

### April 2026: $635M lost, 28 incidents
```
CATEGORY BREAKDOWN:
  Smart Contract:       $328.14M (23 incidents)
  Social Engineering:   $286.60M (3 incidents)
  Infrastructure:       $20.50M  (2 incidents)

TOP INCIDENTS:
  1. Kelp DAO: ~$293M
     → LayerZero OFT bridge exploit (Ethereum + Arbitrum)
     → Cross-chain bridge = highest risk category

  2. Drift Protocol: $285M
     → DPRK-linked operation (UNC4736 / AppleJeus / Citrine Sleet)
     → 6-MONTH infiltration:
       a. Built fake quant trading firm (website, LinkedIn, history)
       b. In-person meetings at crypto conferences
       c. Onboarded vault, deposited >$1M real capital
       d. Ran real trades, participated in strategy discussions
       e. Exploited Solana durable nonce for blind-signing
       f. Two Security Council members blind-signed admin transfer
     → Face-to-face operatives NOT North Korean (third-party intermediaries)
     → Same actors as $50M Radiant Capital hack

SUPPLY CHAIN:
  3. Axios npm compromise (Mar 31)
     → Lead maintainer socially engineered
     → npm + GitHub accounts hijacked
     → 2 malicious versions pushed (v1.14.1, v0.30.4)
     → 80-100M downloads/week exposure
     → ~600,000 installs in 3-hour window
     → 135 endpoints beaconing to C2 infrastructure
     → Affects: crypto frontends, signing servers, oracle relayers

  4. Vercel breach via Context.ai (Apr 19)
     → Third-party tool compromise
     → Access keys, source code, API keys, deployment creds stolen
     → Vercel hosts large share of crypto frontends

ZERO-DAYS:
  5. CVE-2026-31431: Linux kernel "Copy Fail" (CVSS 7.8)
     → Local privilege escalation via algif_aead
     → 732-byte Python script → root on any Linux since 2017
     → Modifies page cache (undetectable by disk forensics)
     → Container breakout risk on cloud infrastructure

  6. CVE-2026-35616: Fortinet FortiClient EMS (CVSS 9.1)
     → Auth bypass + RCE, no credentials needed
     → Actively exploited before advisory

AI AGENT SECURITY:
  7. Google: 32% increase in prompt injection (Nov 2025 - BOZ 2026)
  8. CVE-2025-53773: GitHub Copilot RCE via PR description (CVSS 9.6)
  9. EchoLeak: Microsoft 365 Copilot zero-click data exfiltration
  10. Comment and Control: AI code review agents bypassed via PR titles
```

### May 2026: $59.52M lost, 29 incidents
```
  → Down sharply from April's $635M
  → No single hack carried the month
  → Mini Shai-Hulud npm worm: 1000+ malicious package versions
  → Self-propagating supply chain attack
```

### June 2026: $75.32M lost, 32 incidents
```
  → Up from May's $59.52M
  → Humanity Protocol: $32M (42% of monthly losses)
    → Social engineering attack on $H token keys
    → Phishing campaign targeting macOS users
    → Quantstamp led independent investigation
  → npm supply chain wave hit Red Hat packages
  → PeopleSoft zero-day exploited for 2 weeks before Oracle disclosed
```

### ATTACK PATTERN TRENDS (Q2 2026):
```
1. SOCIAL ENGINEERING > CODE EXPLOITS
   → Drift: $285M (6-month infiltration)
   → Humanity: $32M (phishing)
   → 88% of losses from operational failures
   → DPRK groups using third-party intermediaries

2. SUPPLY CHAIN ATTACKS EXPLODING
   → Axios: 600K installs compromised
   → Mini Shai-Hulud: 1000+ malicious npm packages
   → Vercel via Context.ai: third-party breach
   → Crypto teams use npm for EVERYTHING (frontends, relayers, signers)

3. AI AGENT ATTACKS EMERGING
   → Prompt injection +32% in 3 months
   → GitHub Copilot RCE via PR descriptions
   → Zero-click data exfiltration via M365 Copilot
   → AI code review agents bypassed
   → OWASP #1 LLM vulnerability: prompt injection

4. CROSS-CHAIN BRIDGES STILL HIGHEST RISK
   → Kelp: $293M via LayerZero OFT
   → Bridges = largest single-point-of-failure
   → Multi-chain = multi-attack-surface

5. ZERO-DAYS IN INFRASTRUCTURE
   → Linux kernel: undetectable root escalation
   → Fortinet: auth bypass + RCE
   → Cloud/container breakout risk
   → Crypto runs on this infrastructure
```

---

## 3. INTEGRATED ATTACK PATTERN LIBRARY

### For DeFi Audits (check EVERY protocol):
```
□ Access control: all admin functions gated?
□ Share/token conversion: interest-aware?
□ Oracle: TWAP or spot? Staleness check?
□ Reentrancy: nonReentrant on all external calls?
□ ERC4626: virtual offset for inflation attack?
□ Fee calculation: rounding direction consistent?
□ State machine: all transitions clear stale state?
□ Permissionless functions: unintended side effects?
□ Circuit breakers: can they be bypassed?
□ Cross-contract: return values checked?
```

### For Operational Security (Halborn red team):
```
□ Key management: multi-sig? threshold? hardware wallets?
□ Social engineering: team trained? verification processes?
□ Supply chain: dependencies audited? lock files?
□ Infrastructure: cloud security? container isolation?
□ Monitoring: on-chain alerts? auto-pause?
□ Incident response: plan documented? tested?
□ Compliance: MiCA/DORA/VARA requirements met?
```

### For AI Security (emerging):
```
□ Prompt injection: input sanitization?
□ Agent tool access: least privilege?
□ Code review agents: PR content sanitized?
□ LLM data exfiltration: output filtering?
□ MCP security: tool call validation?
```

---

*BOZAGENTIC · Solodit + Quantstamp Attack Patterns Complete*
*52,697 Solodit findings analyzed · 3 months Security Beat compiled*
*Q2 2026: $770M lost, social engineering + supply chain = top vectors*
