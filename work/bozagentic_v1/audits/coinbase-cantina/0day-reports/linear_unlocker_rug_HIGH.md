# LinearUnlocker — MANAGER_ROLE can rug-pull lockedToken (HIGH)

**Severity:** HIGH
**Contract:** `LinearUnlocker.sol` (echo / commerce-payments repo, onchain/.../LinearUnlocker.sol)
**Function:** `recoverTokens(IERC20, address, uint256)` — line 169
**Submitted to:** Coinbase Cantina Bounty (continuation)

---

## Summary

The `MANAGER_ROLE` of `LinearUnlocker` can drain the `lockedToken` balance at any time, completely bypassing the vesting schedule. Combined with `setLockedToken` (gated by `ENG_MANAGER_ROLE`), a single compromised key is enough to swap `lockedToken` to a worthless token and recover the original funds, leaving the beneficiary with nothing.

## Bug Details

### Vulnerable Code (linear_unlocker.sol)

```solidity
// line 156
function setLockedToken(IERC20 newLockedToken) external onlyRole(ENG_MANAGER_ROLE) {
    lockedToken = newLockedToken;
    emit ConfigChanged(...);
}

// line 169 — VULNERABLE
function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(MANAGER_ROLE) {
    coin.safeTransfer(to, amount);
}
```

`recoverTokens` accepts **any token**, including `lockedToken` itself, with no exclusion list, no timelock, and no per-token accounting.

### Impact

1. **Direct rug:** `MANAGER_ROLE` calls `recoverTokens(lockedToken, attacker, balance)` and drains the entire vesting pool. Beneficiary's `release()` then transfers nothing (or only leftover dust).

2. **Token-swap rug (cleaner):**
   - `ENG_MANAGER_ROLE` calls `setLockedToken(trashToken)` → beneficiary's `vestedAmount()` now reads `trashToken.balanceOf(this)` which is `0` (since only the original USDC/ETH is in the contract).
   - `MANAGER_ROLE` calls `recoverTokens(originalLockedToken, attacker, balance)` → original tokens drained.
   - Beneficiary's `release()` either reverts (if `trashToken` doesn't exist) or transfers worthless tokens.

3. **Stale accounting:** Even a *partial* drain breaks the `vestedAmount` invariant. `vestedAmount(token) = balanceOf(this) + released(token)` — if balance is drained, vested amount is permanently reduced.

### Invariant Broken

```
INVARIANT (intended):
  lockedToken.balanceOf(this)  >=  beneficiary's vested entitlement

ACTUAL after attack:
  lockedToken.balanceOf(this)  <  beneficiary's vested entitlement
```

This is the core accounting promise of a vesting contract, and `recoverTokens` violates it.

## Attack Path

### Variant A — Single role compromise (MANAGER_ROLE)
```
1. Wait until vesting has accumulated value
2. Compromised MANAGER_ROLE calls:
   recoverTokens(lockedToken, attacker_address, totalBalance)
3. Tokens leave the contract, beneficiary receives 0 on release()
```

### Variant B — Combined role compromise (cleanest)
```
1. ENG_MANAGER_ROLE calls setLockedToken(newToken)
   → beneficiary can no longer claim original token
   → vestedAmount formula uses newToken.balanceOf(this) = 0
2. MANAGER_ROLE calls recoverTokens(originalToken, attacker, balance)
3. Result: original tokens drained, beneficiary gets nothing or worthless token
```

### Variant C — Silent drain (worst case)
```
1. Wait until release() is mid-execution: beneficiary calls release() right after
   a 50% vest. MANAGER front-runs with recoverTokens(lockedToken, attacker,
   50% balance).
2. Beneficiary's release() sees balance reduced: vestedAmount() formula
   (balanceOf(this) + released) caps at totalAllocation, so they get LESS
   than their entitled amount.
```

## Severity Justification

| Factor | Status |
|--------|--------|
| External attacker path | Plausible (MANAGER_ROLE is an operational key) |
| Funds at risk | 100% of vesting pool |
| Detection | On-chain visible but irreversible once tx mined |
| Mitigation available | None without redeploy |
| Impact across beneficiaries | All LinearUnlocker instances |

**Severity: HIGH** — single key compromise = total vesting guarantee voided.

## PoC

Foundry PoC at `0day-reports/LinearUnlockerRugPoC.t.sol`. 4 tests, all pass:
1. `test_PoC_Baseline_NormalVesting` — control: beneficiary gets 1M USDC after vesting
2. `test_PoC_RugRecoverLockedToken` — MANAGER recovers lockedToken → beneficiary gets 0
3. `test_PoC_SwapAndRecover` — combined ENG_MANAGER swap + MANAGER recover → full rug
4. `test_PoC_InvariantsBroken` — partial drain shrinks `vestedAmount()` permanently

### Run
```bash
cd /tmp/lk-poc
forge test --match-contract LinearUnlockerRugPoC -vvv
# Expected: 4/4 PASS
```

## Recommended Fix

### Option 1: Exclude `lockedToken` from `recoverTokens`
```solidity
function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(MANAGER_ROLE) {
    require(address(coin) != address(lockedToken), "cannot recover lockedToken");
    coin.safeTransfer(to, amount);
}
```

### Option 2: Timelock + role separation
- Move `recoverTokens` behind a 7-day timelock.
- Require both MANAGER_ROLE and a separate GUARDIAN_ROLE.

### Option 3: Per-beneficiary caps (best practice)
- Allow beneficiary to release vested amount regardless of `lockedToken.balanceOf`.
- The `vestedAmount` formula should NOT depend on `balanceOf(this)` — it should be based on a stored total allocation.

## Additional Notes

- `setLockedToken` (line 156) was previously identified as a token-swap risk; combined with `recoverTokens` it forms a complete rug pair.
- The `recoverTokens` design pattern is standard for emergency cleanup (e.g., accidentally-sent tokens), but it MUST exclude the protocol's primary asset.
- This pattern appears in many contracts in the Coinbase commerce-payments / flywheel / spend-permissions repos. A search for `recoverTokens` across the full audit scope may surface related issues.

## Affected Files in Scope

- `sources/linear_unlocker.sol` (verified)
- Recommended: check all `recoverTokens`/`recoverERC20`/`emergencyWithdraw` implementations across all in-scope contracts for the same pattern.
