# CashbackRewards `maxRewardBps` Cap Bypass via `allocate()` + `send()` Inconsistency

## Severity: MEDIUM

## Summary

The `_validatePaymentReward()` function in `CashbackRewards.sol` enforces a per-payment reward cap (`maxRewardBps`) inconsistently across reward operations. The `ALLOCATE` path correctly counts both `distributed` and `allocated` amounts when checking the cap, but the `SEND` and `DISTRIBUTE` paths only count `distributed`, ignoring any previously `allocated` amount. This allows a campaign manager to bypass the configured `maxRewardBps` cap by first calling `allocate()` up to the cap, then calling `send()` up to the cap again — resulting in a total reward of up to **2x the configured maximum**.

## Vulnerability Details

**File:** `src/hooks/CashbackRewards.sol`
**Function:** `_validatePaymentReward()` (line 292–345)

### Vulnerable Code (lines 324–331):

```solidity
// Payment amount is the captured amount that has not been refunded
uint120 paymentAmount = refundableAmount;
uint120 previouslyRewardedAmount = rewards[campaign][paymentInfoHash].distributed;
//                                                                  ^^^^^^^^^^^
//                                          BUG: only counts distributed, ignores allocated

// If allocating, add the pre-capture and pre-distribution amounts too
if (operation == RewardOperation.ALLOCATE) {
    paymentAmount += capturableAmount;
    previouslyRewardedAmount += rewards[campaign][paymentInfoHash].allocated;
    //                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    //                        allocated ONLY added for ALLOCATE, not SEND/DISTRIBUTE
}
```

### Root Cause

The `allocated` amount is only added to `previouslyRewardedAmount` when `operation == RewardOperation.ALLOCATE`. For `SEND` and `DISTRIBUTE` operations, `previouslyRewardedAmount` only reflects `distributed`, completely ignoring any existing `allocated` balance.

## Attack Scenario

**Setup:**
- Payment amount: 100,000 tokens
- `maxRewardBps`: 5,000 (50%)
- Maximum allowed reward: 50,000 tokens

**Step 1 — `allocate(50,000)`:**
```
previouslyRewarded = distributed(0) + allocated(0) = 0   ← ALLOCATE path counts both
total = 0 + 50,000 = 50,000
maxAllowed = 100,000 * 5000 / 10000 = 50,000
50,000 <= 50,000 → ✅ PASSES
State: allocated = 50,000, distributed = 0
```

**Step 2 — `send(50,000)`:**
```
previouslyRewarded = distributed(0) = 0                  ← SEND path ignores allocated!
total = 0 + 50,000 = 50,000
maxAllowed = 100,000 * 5000 / 10000 = 50,000
50,000 <= 50,000 → ✅ PASSES (but should NOT!)
State: allocated = 50,000, distributed = 50,000
```

**Result:**
- Total rewarded: 50,000 (allocated) + 50,000 (distributed) = **100,000 tokens**
- Configured cap: 50,000 tokens
- **Cap bypassed by 2x** — the buyer receives 100% of the payment as reward instead of the configured 50% maximum.

## Impact

- The `maxRewardBps` parameter exists as a **safety cap** to limit reward exposure per payment. This bug renders it ineffective.
- A compromised or malicious campaign manager can extract up to **2x the intended maximum** reward from campaign funds for any single payment.
- The `DISTRIBUTE` operation has the same inconsistency (line 325 applies to both `SEND` and `DISTRIBUTE`), enabling the same bypass via `allocate()` → `distribute()`.
- While this requires the `MANAGER` role, the cap exists precisely to constrain manager behavior. A manager key compromise would result in 2x the expected damage.

## Proof of Concept

See `poc/CashbackMaxRewardBypassPoC.t.sol` — 6 proofs, all passing:

```
[PASS] test_proof1_allocate_passes_at_cap()
[PASS] test_proof2_send_ignores_allocated()
[PASS] test_proof3_total_exceeds_cap()          ← 10000 > 5000 cap
[PASS] test_proof4_correct_impl_prevents()       ← fix would catch it
[PASS] test_proof5_distribute_also_ignores()
[PASS] test_proof6_max_exploit()                 ← 2x bypass ratio
```

Additionally verified via Z3 SMT solver:
- `SAT` — bypass mathematically proven with concrete model
- `UNSAT` — correct implementation prevents bypass

## Recommended Fix

Change line 325 to always count both `distributed` and `allocated`:

```solidity
// BEFORE (vulnerable):
uint120 previouslyRewardedAmount = rewards[campaign][paymentInfoHash].distributed;

// AFTER (fixed):
uint120 previouslyRewardedAmount = rewards[campaign][paymentInfoHash].distributed
                                 + rewards[campaign][paymentInfoHash].allocated;
```

And remove the redundant addition inside the `ALLOCATE` branch (line 330):

```solidity
// BEFORE:
if (operation == RewardOperation.ALLOCATE) {
    paymentAmount += capturableAmount;
    previouslyRewardedAmount += rewards[campaign][paymentInfoHash].allocated; // remove this
}

// AFTER:
if (operation == RewardOperation.ALLOCATE) {
    paymentAmount += capturableAmount;
    // allocated already counted above
}
```

## Tools Used

| Tool | Result |
|------|--------|
| Manual line-by-line review | **FOUND** |
| Z3 SMT solver | SAT — bypass proven |
| Foundry PoC test | 6/6 PASS |
| Slither | Not detected (logic bug) |
| Mythril | Not detected (logic bug) |
| Aderyn | Not detected (logic bug) |
| Semgrep | Not detected (logic bug) |
| Echidna 50K | PASS (no invariant for this) |
| Medusa 50K | PASS (no invariant for this) |

## Scope

- **Contract:** `CashbackRewards.sol` (Flywheel Tier 1)
- **Address:** Deployed via Flywheel `0x00000f14ad09382841db481403d1775adee1179f` on Base
- **Bounty:** Cantina Coinbase Bounty (Tier 1)
