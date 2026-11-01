SUMMARY:

The recoverTokens function in LinearUnlocker lacks an exclusion for the
lockedToken, allowing a compromised MANAGER_ROLE to drain the entire
vesting pool. Combined with setLockedToken controlled by ENG_MANAGER_ROLE,
a single compromised key can swap the lockedToken to a worthless asset
and recover the original funds, leaving the beneficiary with nothing.

DESCRIPTION:

While reviewing LinearUnlocker I noticed something off about the
recoverTokens function. It's gated by MANAGER_ROLE, which is fine for
normal "oops someone sent the wrong token" cleanup. But it accepts ANY
IERC20 as input with no exclusion list.

A compromised MANAGER_ROLE can drain lockedToken directly:

    recoverTokens(lockedToken, attacker, totalBalance)

The beneficiary's release() will then transfer 0 because balanceOf(this)
is 0 and vestedAmount reads balanceOf(this) + released. The entire
vesting guarantee goes away with one call.

Worse, ENG_MANAGER_ROLE has setLockedToken which can swap the lockedToken
to anything. Combine them and the rug is cleaner:

    1. ENG_MANAGER calls setLockedToken(TRASH)
       - vestedAmount() now reads TRASH.balanceOf(this) = 0
       - beneficiary entitlement collapses immediately
    2. MANAGER calls recoverTokens(originalToken, attacker, balance)
       - original tokens drained, beneficiary gets nothing

PoC (Foundry, 4 tests pass with
forge test --match-contract LinearUnlockerRugPoC -vvv):

Test 1 — baseline. After vesting completes, beneficiary release() gets
the full 1M USDC. PASS.

Test 2 — direct drain. Compromised imManager calls
recoverTokens(usdc, attacker, totalBalance). Attacker balance = 1M USDC,
beneficiary release() returns 0. PASS.

Test 3 — swap + drain. ENG_MANAGER swaps lockedToken to TRASH,
beneficiary release() returns 0 (TRASH balance = 0), then MANAGER
recovers the original 1M USDC. PASS.

Test 4 — invariant break. A 50% drain permanently shrinks
vestedAmount() because the formula depends on live balance, not stored
allocation. PASS.

Severity rationale:
- Impact: 100% of lockedToken at risk, multiple beneficiaries, no
  recovery once tx mined.
- Likelihood: medium — MANAGER_ROLE and ENG_MANAGER_ROLE are operational
  keys, not cold multisigs, so compromise via phishing, key leak, or
  rogue insider is realistic.
- Severity: critical under Cantina matrix because impact ceiling is
  full loss and multiple independent attack vectors exist.

Recommended fix:
Add an exclusion in recoverTokens:
    require(address(coin) != address(lockedToken), "cannot recover lockedToken");

Optional: timelock recoverTokens and setLockedToken behind a separate
guardian role.
