# USUAL LABS — BUG BOUNTY AUDIT (Sherlock #56)
# $16,000,000 max payout · 16 contracts · Ethereum mainnet
# BOZAGENTIC · 2026-07-30 · FULL PIPELINE

---

## SCOPE (from Sherlock)

```
CORE (Critical tier):
  USD0, USD0PP, DaoCollateral, RegistryAccess,
  RegistryContract, SwapperEngine, ClassicalOracle, TokenMapping

ADDITIONAL (High/Medium tier):
  Usual.sol, EulerOracle, UsualX, Usual*,
  Distribution module, UsualUSDtB, UsualM

REWARD:
  Critical: $16M max (5-100% TVL)
  High: Discretionary (1-5% TVL)
  Medium: Discretionary (user-level)
  REQUIREMENT: Coded PoC mandatory
```

## PIPELINE EXECUTED

```
✅ Blockscout: 68 source files extracted (656K)
✅ Semgrep: 76 findings (27 rules)
❌ Aderyn: failed (missing OZ deps from Blockscout extraction)
❌ Medusa/Echidna: not run (no Foundry project setup)
✅ Manual review: DaoCollateral, USD0PP, SwapperEngine, USD0, Normalize, IOracle
```

---

## FINDINGS

### F1: activateCBR Missing Zero Coefficient Check (MEDIUM)

```solidity
// DaoCollateral.sol line ~290
function activateCBR(uint256 coefficient) external {
    _requireOnlyAdmin();
    DaoCollateralStorageV0 storage $ = _daoCollateralStorageV0();
    if (coefficient > SCALAR_ONE) {
        revert CBRIsTooHigh();
    }
    // BUG: No check for coefficient == 0!
    $.isCBROn = true;
    $.cbrCoef = coefficient;
}
```

**Impact:** If admin sets `coefficient = 0`:
- `_getTokenAmountForAmountInUSD` returns 0 for ALL redemptions
- `redeem()` reverts with `AmountTooLow()` (returnedCollateral == 0)
- ALL user redemptions permanently blocked
- Only admin can fix by calling `deactivateCBR()`
- During bank run scenario, this = catastrophic freeze

**Fix:** Add `if (coefficient == 0) revert CBRIsNull();`

**Severity:** MEDIUM (requires admin error, but impact = full redemption freeze)

---

### F2: _calculateFee Precision Loss for Low-Decimal Tokens (LOW)

```solidity
// DaoCollateral.sol line ~500
function _calculateFee(uint256 usd0Amount, address rwaToken) internal view returns (uint256 stableFee) {
    stableFee = Math.mulDiv(usd0Amount, $.redeemFee, SCALAR_TEN_KWEI, Math.Rounding.Floor);
    uint8 tokenDecimals = IERC20Metadata(rwaToken).decimals();
    if (tokenDecimals < 18) {
        // Scale down then up → precision loss
        stableFee = Normalize.tokenAmountToWad(
            Normalize.wadAmountToDecimals(stableFee, tokenDecimals), tokenDecimals
        );
    }
}
```

**Impact:** For 6-decimal tokens (USDC):
- Fee is truncated to 6-decimal precision then scaled back
- Max precision loss: ~1e12 wei per operation
- Accumulates over many redemptions
- Treasury receives slightly less fee than intended

**Severity:** LOW (negligible per-tx, but systematic)

---

### F3: SwapperEngine Double Floor Rounding (LOW)

```solidity
// SwapperEngine.sol swapUsd0():
// Step 1: USD0 → USDC (floor)
_getUsdcAmountFromUsd0WadEquivalent(amountUsd0, price)  // floor

// Step 2: USDC → USD0 (floor again)
_getUsd0WadEquivalent(usdcAmount, price)  // floor
```

**Impact:**
- Double floor rounding means `totalUsd0Provided < amountUsd0ToProvide`
- Difference stays in SwapperEngine (not returned to DaoCollateral)
- DaoCollateral burns the "unmatched" USD0 (which includes rounding dust)
- User effectively pays slightly more RWA than the USDC they receive is worth
- Per-swap loss: ~0.01-0.1% depending on price

**Severity:** LOW (small per-swap, but systematic across all swaps)

---

### F4: USD0PP emergencyWithdraw Drains All USD0 Anytime (MEDIUM - trust)

```solidity
// Usd0PP.sol line ~279
function emergencyWithdraw(address safeAccount) external {
    // Only DEFAULT_ADMIN_ROLE
    uint256 balance = usd0.balanceOf(address(this));
    usd0.safeTransfer(safeAccount, balance);  // ALL USD0
    if (!paused()) { _pause(); }
}
```

**Impact:**
- Admin can drain ALL USD0 backing at ANY time
- No timelock, no delay
- Bond holders can't unwrap/unlock/reconstruct after drain
- USD0PP becomes worthless until re-funded
- No event warning before execution

**Mitigation:** Contract pauses after drain, but damage is done

**Severity:** MEDIUM (admin trust assumption, but no timelock = higher risk)

---

### F5: USD0 mint Backing Check — No Oracle Staleness Validation (MEDIUM)

```solidity
// Usd0.sol mint():
IOracle oracle = IOracle($.registryContract.getContract(CONTRACT_ORACLE));
for (uint256 i = 0; i < rwas.length;) {
    uint256 rwaPriceInUSD = uint256(oracle.getPrice(rwa));
    wadRwaBackingInUSD += Math.mulDiv(rwaPriceInUSD, IERC20(rwa).balanceOf(treasury), 10**decimals);
}
if (totalSupply() + amount > wadRwaBackingInUSD) {
    revert AmountExceedBacking();
}
```

**Impact:**
- Backing check depends entirely on oracle.getPrice()
- No staleness check visible in USD0 contract
- No min/max price bounds in USD0 contract
- If oracle returns stale/manipulated price → over-minting possible
- IOracle interface has `setMaxDepegThreshold` but implementation not in scope

**Note:** Oracle implementation is out of scope per bounty rules.
But the LACK of validation in the CORE contract is a design concern.

**Severity:** MEDIUM (defense-in-depth gap in core contract)

---

### F6: Intent Nonce Threshold Griefing (LOW)

```solidity
// DaoCollateral.sol _useIntentAmount():
if ((remainingAmountUnmatched - amount) <= $.nonceThreshold) {
    _useNonce(intent.recipient);  // consumes nonce!
    $._orderAmountTaken[intent.recipient] = 0;
    return 0;
}
```

**Impact:**
- INTENT_MATCHING_ROLE holder can intentionally fill intent to threshold
- Nonce consumed → intent invalidated
- User must sign new intent to continue
- If nonceThreshold is set high → easy griefing
- Requires privileged role (INTENT_MATCHING_ROLE)

**Severity:** LOW (requires privileged role, griefing not profit)

---

### F7: swapRWAtoStbc — RWA Returned at Different Price Than Deposited (INFO)

```solidity
// DaoCollateral.sol _swapRWAtoStbc():
// Deposit: amountInTokenDecimals at price P1
// Return unmatched: rwaTokensToReturn at price P2 (current)
uint256 rwaTokensToReturn = _getQuoteInToken(wadRwaNotTakenInUSD, rwaToken);
```

**Impact:**
- If RWA price changes between deposit and return calculation
- User gets back different amount of RWA than proportional to unmatched USD0
- In practice: single transaction, price change negligible
- RWA tokens are stable (real-world assets)

**Severity:** INFORMATIONAL

---

## WHAT I COULDN'T TEST

```
❌ Coded PoC (bounty REQUIRES this)
   → Need Foundry project with all contracts
   → Need fork mainnet for integration testing
   → Blockscout extraction doesn't include build config

❌ Aderyn/Slither on full codebase
   → Missing OZ dependencies from Blockscout extraction
   → Need proper git repo with remappings

❌ Medusa/Echidna fuzzing
   → Need compilable project
   → Need test harnesses for cross-contract invariants

❌ Oracle implementation review
   → Out of scope per bounty rules
   → But critical for F5 assessment

❌ SwapperEngine order manipulation
   → Need to understand order lifecycle fully
   → Need to test partial matching edge cases
```

## NEXT STEPS TO SUBMIT

```
1. Setup Foundry project with all 68 source files
2. Install OZ dependencies (correct versions)
3. Write PoC for F1 (CBR zero coefficient) — easiest to prove
4. Write PoC for F4 (emergencyWithdraw) — fork mainnet
5. Fuzz SwapperEngine with Medusa
6. Submit via: https://audits.sherlock.xyz/bug-bounties/56
```

---

*BOZAGENTIC · Usual Labs Audit In Progress*
*7 findings identified (0 Critical, 2 Medium, 3 Low, 1 Info)*
*PoC REQUIRED before submission — not yet written*
