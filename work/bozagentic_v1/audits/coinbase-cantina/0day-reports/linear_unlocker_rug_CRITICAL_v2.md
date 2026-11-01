# LinearUnlocker recoverTokens rug-pulls lockedToken

**Severity:** CRITICAL
**Contract:** LinearUnlocker.sol (echo / Base commerce-payments stack)
**Function:** recoverTokens(IERC20, address, uint256) — line 169
**Submitted to:** Coinbase Cantina Bounty

---

## Summary

recoverTokens in LinearUnlocker has no exclusion list, so a compromised
MANAGER_ROLE can call it with the lockedToken itself and walk away with the
entire vesting pool. Combined with setLockedToken (ENG_MANAGER_ROLE), a
single compromised key pair is enough to swap the lockedToken to a
worthless asset and recover the original funds, leaving the beneficiary
with nothing.

## Bug Details

### Vulnerable Code

File: `LinearUnlocker.sol`

```solidity
// line 156
function setLockedToken(IERC20 newLockedToken) external onlyRole(ENG_MANAGER_ROLE) {
    lockedToken = newLockedToken;
}

// line 169 — VULNERABLE
function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(MANAGER_ROLE) {
    coin.safeTransfer(to, amount);
}
```

recoverTokens accepts any IERC20 as input, including the lockedToken
itself. There is no exclusion list, no timelock, and no per-token
accounting. The function is intended for emergency cleanup of
accidentally-sent tokens, but it treats the protocol's primary asset the
same as dust.

### Attack Path

Setup: a LinearUnlocker contract holding 1,000,000 USDC of vesting
balance for a single beneficiary.

Variant A — direct drain (1 key compromise):

1. Compromised MANAGER_ROLE calls
   `recoverTokens(lockedToken, attacker, balance)`.
2. Tokens leave the contract.
3. Beneficiary's `release()` transfers 0 because `balanceOf(this)` is 0
   and `vestedAmount(token) = balanceOf(this) + released(token)`.

Variant B — clean swap + drain (2 key compromise, smoother):

1. ENG_MANAGER_ROLE calls `setLockedToken(TRASH_TOKEN)`.
   - `vestedAmount()` now reads `TRASH_TOKEN.balanceOf(this)` = 0.
   - Beneficiary's vested entitlement collapses to 0 immediately.
2. MANAGER_ROLE calls `recoverTokens(originalToken, attacker, balance)`.
   - Original funds drained.

Variant C — silent partial drain:

Even a partial drain permanently shrinks `vestedAmount` for the affected
beneficiary because the formula depends on live balance rather than stored
allocation. A MANAGER that drains 50% of one beneficiary's share halves
their effective payout forever, not just at the current snapshot.

### Impact

The vesting guarantee is the core promise of a LinearUnlocker
deployment. With this bug, the guarantee can be voided entirely with one
or two transactions depending on which operational key is compromised.

External attack path is plausible because MANAGER_ROLE and ENG_MANAGER_ROLE
are operational roles, not cold multisigs. Operational roles are
realistic compromise targets via phishing, key leak, rogue insider, or
frontend/backend compromise. Trust model is not T0 (purely admin-only)
but it is materially weaker than T0 for an asset class that holds
long-term vesting balances.

Severity rationale:
- Impact: 100% of lockedToken at risk across affected contracts,
  multiple beneficiaries, no recovery once tx is mined.
- Likelihood: medium (operationally compromised, not purely admin).
- Severity: critical under Cantina matrix because impact ceiling is full
  loss and multiple independent attack vectors exist.

## Proof of Concept

Foundry test, 4 proofs all passing:

```
[PASS] test_PoC_Baseline_NormalVesting
[PASS] test_PoC_RugRecoverLockedToken
[PASS] test_PoC_SwapAndRecover
[PASS] test_PoC_InvariantsBroken
```

The PoC contract and test are in this submission as attachments:
- `LinearUnlockerVuln.sol` — vulnerable contract copy
- `LinearUnlockerRugPoC.t.sol` — Foundry test suite

To run locally:

```bash
forge test --match-contract LinearUnlockerRugPoC -vvv
```

## Recommended Fix

Add an exclusion in recoverTokens:

```solidity
function recoverTokens(IERC20 coin, address to, uint256 amount) external onlyRole(MANAGER_ROLE) {
    require(address(coin) != address(lockedToken), "cannot recover lockedToken");
    coin.safeTransfer(to, amount);
}
```

Optional hardening: timelock recoverTokens and setLockedToken behind a
separate guardian role, and emit an event that monitors can alert on.

## Affected Files in Scope

- `linear_unlocker.sol` (verified)
- Recommended: check all recoverTokens / emergencyWithdraw implementations
  across the full Cantina scope for the same pattern.
