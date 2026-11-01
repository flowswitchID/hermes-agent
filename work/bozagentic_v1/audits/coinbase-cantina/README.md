# Coinbase Cantina Bounty — CashbackRewards maxRewardBps Cap Bypass

## Finding

**Severity:** MEDIUM
**Contract:** `CashbackRewards.sol` (Flywheel Tier 1, Base)
**Function:** `_validatePaymentReward()` line 325

## Bug

`SEND` and `DISTRIBUTE` operations ignore the `allocated` amount when checking the `maxRewardBps` cap. Only `ALLOCATE` counts both `distributed + allocated`. This allows bypassing the cap by calling `allocate(cap)` then `send(cap)` — total reward = 2x the configured maximum.

## Contents

```
report/     — Full vulnerability report (Markdown)
poc/        — Foundry PoC test (6 proofs, all PASS)
source/     — Vulnerable contract source
tools-output/
  z3-proof-output.txt      — Z3 SMT proof (SAT = bypass confirmed)
  cashback_z3.py           — Z3 proof script
  foundry-poc-output.txt   — Foundry test output (6/6 PASS)
```

## How to Run PoC

```bash
cd /tmp/flywheel
forge test --match-contract CashbackMaxRewardBypassPoC -vvv
```

## Fix

```solidity
// Line 325 — change from:
uint120 previouslyRewardedAmount = rewards[campaign][paymentInfoHash].distributed;

// To:
uint120 previouslyRewardedAmount = rewards[campaign][paymentInfoHash].distributed
                                 + rewards[campaign][paymentInfoHash].allocated;
```

## Audit Scope

- 10,000+ lines across 30+ contracts, 7 repos
- 14 tools: Slither, Mythril, Aderyn, Semgrep, Echidna, Medusa, Halmos, Z3, Foundry tests/fuzz/invariant
- 1 valid MEDIUM finding (this one)
