# ARCADIA FINANCE — SECURITY AUDIT NOTES
# Lending Pool + Tranche + DebtToken
# Source: github.com/arcadia-finance/arcadia-lending
# BOZAGENTIC · 2026-07-29

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────┐
│                    LENDING POOL                          │
│  (Guardian + TrustedCreditor + DebtToken + InterestRate)│
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Tranche  │  │ Tranche  │  │ Treasury │             │
│  │ (Senior) │  │ (Junior) │  │          │             │
│  │ ERC4626  │  │ ERC4626  │  │          │             │
│  └────┬─────┘  └────┬─────┘  └──────────┘             │
│       │              │                                  │
│       └──────┬───────┘                                  │
│              │ deposit/withdraw                          │
│              ▼                                          │
│  ┌─────────────────────────────────────────┐           │
│  │         LendingPool Core                 │           │
│  │  - borrow / repay                        │           │
│  │  - doActionWithLeverage                  │           │
│  │  - liquidateVault / settleLiquidation    │           │
│  │  - interest accrual (compound)           │           │
│  │  - skim (rounding surplus → treasury)    │           │
│  └─────────────────────────────────────────┘           │
│              │                                          │
│              ▼                                          │
│  ┌─────────────────────────────────────────┐           │
│  │         Vault (external)                 │           │
│  │  - Collateral management                 │           │
│  │  - Health check                          │           │
│  │  - vaultManagementAction                 │           │
│  └─────────────────────────────────────────┘           │
│              │                                          │
│              ▼                                          │
│  ┌─────────────────────────────────────────┐           │
│  │         Liquidator (external)            │           │
│  │  - Dutch auction                         │           │
│  │  - startAuction / endAuction             │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

**Key design:**
- Tranches are ERC4626 (Solmate) — LPs deposit/withdraw via Tranche
- DebtToken is ERC4626 (inverted rounding) — tracks vault debt
- LendingPool does accounting, interest, liquidation
- Vault holds collateral, does health checks
- Liquidator runs Dutch auctions for undercollateralized vaults

---

## FINDINGS

### FINDING 1: No Reentrancy Guard — CEI Pattern Only
**Severity: INFORMATIONAL**
**Status: By Design (fragile)**

```solidity
// LendingPool.sol — NO nonReentrant modifier anywhere
function borrow(uint256 amount, address vault, address to, bytes3 referrer) external ... {
    _deposit(amountWithFee, vault);           // state
    totalRealisedLiquidity += ...;            // state
    realisedLiquidityOf[treasury] += ...;     // state
    IVault(vault).isVaultHealthy(...);        // external call
    asset.safeTransfer(to, amount);           // external call ← REENTRANCY POINT
}
```

**Analysis:** Protocol relies on Checks-Effects-Interactions pattern. State changes happen before external calls. Reentrancy would find state already updated.

**Risk:** Works for current code, but fragile. Any future modification that moves state changes after external calls would introduce reentrancy. No safety net.

**Recommendation:** Add `nonReentrant` modifier as defense-in-depth. Gas cost is minimal (~5k per call).

---

### FINDING 2: `doActionWithLeverage` — No Redundant Health Check
**Severity: LOW**
**Status: Trust Assumption**

```solidity
function doActionWithLeverage(...) external ... {
    _deposit(amountBorrowedWithFee, vault);   // mint debt
    asset.safeTransfer(actionHandler, amountBorrowed);  // send funds
    
    // Vault does health check internally
    (address trustedCreditor, uint256 vaultVersion) = 
        IVault(vault).vaultManagementAction(actionHandler, actionData);
    require(trustedCreditor == address(this) && isValidVersion[vaultVersion]);
    // ⚠️ NO explicit isVaultHealthy() check here!
}
```

**vs `borrow()` which DOES check:**
```solidity
(bool isHealthy, address trustedCreditor, uint256 vaultVersion) =
    IVault(vault).isVaultHealthy(0, maxWithdraw(vault));
require(isHealthy && trustedCreditor == address(this) && isValidVersion[vaultVersion]);
```

**Analysis:** `doActionWithLeverage` trusts the Vault to perform health check inside `vaultManagementAction`. If the Vault implementation has a bug in its health check, the LendingPool has no redundant safety net.

**Attack scenario:** If a malicious/buggy `actionHandler` can manipulate the Vault's internal state such that `vaultManagementAction` returns success without proper collateralization check, the LendingPool would accept an undercollateralized position.

**Mitigation in current code:** The Vault is deployed by Arcadia's Factory (trusted). But this is a single point of failure.

**Recommendation:** Add explicit `isVaultHealthy()` check after `vaultManagementAction` returns, as redundant safety.

---

### FINDING 3: `donateToTranche` — Inflation Mitigation Threshold
**Severity: INFORMATIONAL**
**Status: Mitigated (arbitrary threshold)**

```solidity
function donateToTranche(uint256 trancheIndex, uint256 assets) external ... {
    require(ERC4626(tranche).totalSupply() >= 10 ** decimals, "LP_DTT: Insufficient shares");
    ...
    realisedLiquidityOf[tranche] += assets;
    totalRealisedLiquidity += SafeCastLib.safeCastTo128(assets);
}
```

**Analysis:** The `10^decimals` threshold prevents first-minter inflation attack:
- USDC (6 dec): requires ≥ 1,000,000 shares (= 1 USDC) before donation allowed
- WETH (18 dec): requires ≥ 10^18 shares (= 1 WETH) before donation allowed

**Why it works:** If attacker deposits `10^decimals` first (getting proportional shares), then donates X, the attacker's shares appreciate proportionally with all other shares. No profit possible — donation is pure loss for attacker.

**Mathematical proof:**
```
Attacker deposits D = 10^decimals → gets D shares
Attacker donates X → totalAssets = D + X, totalSupply = D
Victim deposits Y → gets Y * D / (D + X) shares
Attacker redeems D shares → gets D * (D + X + Y) / (D + Y*D/(D+X))
                         = D * (D + X + Y) * (D + X) / (D*(D+X) + Y*D)
                         = (D + X + Y) * (D + X) / (D + X + Y)
                         = D + X
Attacker's net: (D + X) - D - X = 0. NO PROFIT. ✅
```

**Residual risk:** The threshold is arbitrary. For WETH, 1 WETH (~$1900) is a low bar. An attacker could deposit 1 WETH, then the donation is allowed. But as proven above, they can't profit from it.

---

### FINDING 4: Solmate ERC4626 — No Virtual Shares (Mitigated by Architecture)
**Severity: INFORMATIONAL**
**Status: Mitigated by design**

```solidity
// Tranche uses Solmate ERC4626 — NO virtual shares protection
contract Tranche is ITranche, ERC4626, Owned { ... }

// But totalAssets() reads from LendingPool, NOT balanceOf(this)
function totalAssets() public view override returns (uint256 assets) {
    assets = lendingPool.liquidityOf(address(this));
}
```

**Why standard inflation attack doesn't work:**
- Attacker sends tokens directly to Tranche → NOT counted in `totalAssets()` (reads from LendingPool's `realisedLiquidityOf`)
- Only `depositInLendingPool` and `donateToTranche` increase `realisedLiquidityOf`
- `donateToTranche` has the `10^decimals` threshold (Finding 3)

**Side effect:** Tokens accidentally sent to the Tranche contract are UNRECOVERABLE. They sit in the Tranche but aren't counted in `totalAssets()`. No function to rescue them.

---

### FINDING 5: `skim()` — Permissionless but Safe
**Severity: INFORMATIONAL**
**Status: By Design**

```solidity
function skim() external processInterests {
    require(auctionsInProgress == 0, "LP_S: Auctions Ongoing");
    uint256 delta = asset.balanceOf(address(this)) + realisedDebt - totalRealisedLiquidity;
    unchecked {
        totalRealisedLiquidity += SafeCastLib.safeCastTo128(delta);
        realisedLiquidityOf[treasury] += delta;
    }
}
```

**Analysis:**
- `delta` = actual balance + debt - claimable liquidity = rounding surplus
- Always ≥ 0 in normal operation (ERC4626 rounds in pool's favor)
- Surplus goes to treasury (otherwise lost forever)
- Blocked during auctions (debt burned but proceeds not yet received)

**Can delta be negative?** No, because:
- Deposits: balance += X, liquidity += X (balanced)
- Withdrawals: balance -= X, liquidity -= X (balanced)
- Borrows: balance -= X, debt += X+fee, liquidity += fee (balanced)
- Repays: balance += X, debt -= X (balanced)
- Interest: debt += I, liquidity += I (balanced)
- Rounding: always favors pool → delta ≥ 0

**Not exploitable.** ✅

---

### FINDING 6: Interest Rate Manipulation via Flash Deposit
**Severity: LOW**
**Status: Known limitation, not profitable**

```solidity
function updateInterestRate() external processInterests { }
// _updateInterestRate(realisedDebt, totalRealisedLiquidity)
// Rate based on utilization = debt / liquidity
```

**Attack:**
1. Flash deposit huge amount → liquidity spikes → utilization drops → rate drops
2. Borrow at lower rate
3. Withdraw deposit

**Why not profitable:**
- Deposit goes through Tranche (ERC4626 share minting has rounding costs)
- Borrow pays origination fee (0.1-2.55%)
- Rate change is temporary (next sync recalculates)
- Net cost > rate savings for any reasonable amount

**Recommendation:** Consider adding a minimum deposit duration for rate-affecting deposits, or use time-weighted average utilization.

---

### FINDING 7: `liquidateVault` — Debt Burned Before Auction Settled
**Severity: INFORMATIONAL**
**Status: By Design (mitigated)**

```solidity
function liquidateVault(address vault) external ... {
    uint256 openDebt = maxWithdraw(vault);
    ILiquidator(liquidator).startAuction(vault, openDebt, maxInitiatorFee);
    ++auctionsInProgress;
    _withdraw(openDebt, vault, vault);  // BURN DEBT NOW
    // Auction proceeds come LATER in settleLiquidation()
}
```

**Temporary state during auction:**
- `realisedDebt` decreased (debt burned)
- `totalRealisedLiquidity` NOT decreased
- Pool balance NOT increased (proceeds in Liquidator)
- → `balance + debt < liquidity` (temporarily "insolvent" on paper)

**Mitigations:**
- `skim()` blocked during auctions (`auctionsInProgress == 0` required)
- Tranche deposits/withdrawals blocked (`notDuringAuction` modifier)
- `withdrawFromLendingPool` still callable but limited by actual balance

**Residual risk:** Treasury can call `withdrawFromLendingPool` during auction. If pool balance is insufficient (funds in auction), transfer reverts. No loss, just temporary illiquidity.

---

### FINDING 8: `creditAllowance` — Silent Underflow Revert
**Severity: INFORMATIONAL**
**Status: Safe but bad UX**

```solidity
if (vaultOwner != msg.sender) {
    uint256 allowed = creditAllowance[vault][vaultOwner][msg.sender];
    if (allowed != type(uint256).max) {
        creditAllowance[vault][vaultOwner][msg.sender] = allowed - amountWithFee;
        // ⚠️ If allowed < amountWithFee → underflow → revert (no custom error)
    }
}
```

**Analysis:** Solidity 0.8+ reverts on underflow. No funds at risk. But the revert has no descriptive error message (just "arithmetic underflow"). Bad UX for integrators.

**Recommendation:** Add explicit check: `require(allowed >= amountWithFee, "LP_B: INSUFFICIENT_ALLOWANCE")`

---

### FINDING 9: Tranche `withdraw` — Allowance Check Uses Shares, Not Assets
**Severity: INFORMATIONAL**
**Status: Correct but potentially confusing**

```solidity
function withdraw(uint256 assets, address receiver, address owner_) public override ... {
    shares = previewWithdrawAndSync(assets);
    if (msg.sender != owner_) {
        uint256 allowed = allowance[owner_][msg.sender];
        if (allowed != type(uint256).max) {
            allowance[owner_][msg.sender] = allowed - shares;  // ← shares, not assets
        }
    }
    _burn(owner_, shares);
    lendingPool.withdrawFromLendingPool(assets, receiver);
}
```

**Analysis:** ERC4626 standard specifies that `withdraw` allowance is denominated in SHARES (not assets). This is correct per spec. But integrators might expect asset-denominated allowance.

---

### FINDING 10: `processInterests` — Rate Update After Interactions
**Severity: INFORMATIONAL**
**Status: Analyzed, safe**

```solidity
modifier processInterests() {
    _syncInterests();        // BEFORE: realize pending interest
    _;                       // FUNCTION BODY (includes external calls)
    _updateInterestRate(...); // AFTER: update rate based on new state
}
```

**Analysis:** `_updateInterestRate` runs after external calls (transfers, vault interactions). If reentrancy occurs:
- Inner call: sync (no-op, same block) → execute → update rate
- Outer call: update rate again with final state

Result: rate updated twice, final state is correct. No exploitation path found.

---

## OVERALL ASSESSMENT

```
Security Score: 8.5/10

Strengths:
  ✅ ERC4626 inflation attack properly mitigated (architecture-level)
  ✅ CEI pattern consistently applied
  ✅ Auction mechanism prevents JIT liquidity attacks
  ✅ Tranche locking during auctions prevents frontrunning
  ✅ Debt token is non-transferable (prevents debt trading exploits)
  ✅ Borrow cap + supply cap limit exposure
  ✅ Interest calculation uses LogExpMath (precise compound interest)
  ✅ SafeCastLib prevents silent overflow in uint128 storage

Weaknesses:
  ⚠️ No reentrancy guard (relies solely on CEI)
  ⚠️ doActionWithLeverage trusts Vault for health check
  ⚠️ Interest rate manipulable (though not profitably)
  ⚠️ Tokens sent to Tranche are unrecoverable

NOT FOUND:
  ❌ No critical vulnerabilities
  ❌ No direct fund loss vectors
  ❌ No access control bypasses
  ❌ No oracle manipulation (no internal oracle)
```

---

## COMPARISON WITH BASIN BUG

```
Basin bug:  sync() reads balanceOf() instead of stored reserves
            → donation attack → LP inflation
            
Arcadia:    totalAssets() reads from LendingPool's realisedLiquidityOf
            → direct token transfers DON'T affect share price
            → donateToTranche has threshold check
            → NOT vulnerable to same attack pattern ✅
```

Arcadia learned from the ERC4626 inflation attack class. Their architecture (separating accounting from token balance) is a robust mitigation.

---

## RECOMMENDATIONS FOR BUG BOUNTY

```
This codebase is WELL-AUDITED and well-designed.
Low probability of finding CRITICAL/HIGH bugs in LendingPool/Tranche/DebtToken.

Better targets within Arcadia ecosystem:
  1. Vault implementation (vault-v2 repo) — complex action logic
  2. Liquidator — Dutch auction mechanics, timing attacks
  3. ActionHandler integrations — external DeFi interactions
  4. Oracle/risk module — collateral valuation
  5. Cross-contract composability — Vault + LendingPool + external DEX

The LendingPool core is solid. Look at the EDGES (integrations, external calls).
```

---

---

## ADDITIONAL FINDINGS (InterestRateModule + Guardian + Cross-Contract)

### FINDING 11: Interest Rate — uint80 Truncation in Event
**Severity: INFORMATIONAL**
**Status: Safe (event only)**

```solidity
// InterestRateModule.sol line 106
emit InterestRate(uint80(interestRate = _calculateInterestRate(utilisation)));
```

**Analysis:** `interestRate` stored as uint256, but emitted as uint80. Max uint80 = 1.2e24. Max possible rate = baseRate(uint72) + lowSlope(uint72) + highSlope(uint72) ≈ 3 × 4.7e21 = 1.4e22. Well within uint80 range. No truncation risk.

**But:** If owner sets extreme config values (all uint72 max), rate could theoretically exceed uint80. Event would truncate. Off-chain indexers would see wrong rate. On-chain storage would be correct.

---

### FINDING 12: Guardian — 30-Day Forced Unpause Window
**Severity: INFORMATIONAL**
**Status: By Design (good)**

```solidity
function unPause() external {
    require(block.timestamp > pauseTimestamp + 30 days, "G_UP: Cannot unPause");
    // ANY user can call this after 30 days
}
```

**Analysis:** Anti-hostage mechanism. If guardian pauses and owner doesn't fix within 30 days, anyone can unpause. Users get 2-day window (32-day re-pause cooldown) to withdraw.

**Attack scenario:** Malicious guardian pauses → waits 30 days → forced unpause → immediately re-pauses?
**No:** Re-pause requires `block.timestamp > pauseTimestamp + 32 days`. So after forced unpause at day 30, guardian must wait 2 more days before re-pausing. Users have that window.

**Well-designed.** ✅

---

### FINDING 13: `unPause` — Owner Can Only Unpause, Not Pause
**Severity: INFORMATIONAL**
**Status: By Design (good separation of powers)**

```solidity
function unPause(bool, bool, bool, bool, bool) external onlyOwner {
    repayPaused = repayPaused && repayPaused_;  // can only go true→false
    // ...
}
```

**Analysis:** `AND` logic means owner can ONLY unpause (true && false = false). Cannot set false→true. Only guardian can pause. Good separation:
- Guardian: emergency pause (fast, single account)
- Owner: controlled unpause (deliberate, per-function)

---

### FINDING 14: Cross-Contract — Vault `vaultManagementAction` Trust Boundary
**Severity: MEDIUM**
**Status: Architecture risk**

```
LendingPool.doActionWithLeverage()
  → asset.safeTransfer(actionHandler, amountBorrowed)  // FUNDS SENT
  → IVault(vault).vaultManagementAction(actionHandler, actionData)  // TRUST
  → require(trustedCreditor == address(this) && isValidVersion[vaultVersion])
```

**Attack surface:**
1. `actionHandler` receives borrowed funds BEFORE vault action executes
2. Vault calls `actionHandler` with `actionData` (user-controlled bytes)
3. If `actionHandler` is malicious/buggy → can drain vault collateral
4. Vault's health check is the ONLY safety net

**Why MEDIUM not HIGH:**
- Vault is deployed by Arcadia Factory (trusted)
- `actionHandler` must be whitelisted by Vault (assumed from interface)
- But: if a whitelisted actionHandler has a bug → funds at risk

**What we CAN'T verify without vault-v2 source:**
- How does Vault validate actionHandler?
- What restrictions does Vault place on actionData?
- Does Vault check health BEFORE or AFTER actionHandler executes?
- Can actionHandler call back into LendingPool (reentrancy via Vault)?

---

### FINDING 15: Cross-Contract — Liquidator `startAuction` Trust Boundary
**Severity: LOW**
**Status: Trust assumption**

```solidity
function liquidateVault(address vault) external ... {
    uint256 openDebt = maxWithdraw(vault);
    liquidationInitiator[vault] = msg.sender;
    ILiquidator(liquidator).startAuction(vault, openDebt, maxInitiatorFee);
    ++auctionsInProgress;
    _withdraw(openDebt, vault, vault);  // burn debt
}
```

**Analysis:**
- `liquidator` is immutable (set in constructor) → trusted
- But: if Liquidator contract has a bug in auction mechanics → bad debt
- `openDebt` passed to Liquidator → if Liquidator doesn't validate → could auction for wrong amount
- Debt burned immediately → if auction fails → bad debt socialized to junior tranche

**What we CAN'T verify without liquidator source:**
- Dutch auction pricing curve
- Minimum bid enforcement
- Auction timeout handling
- What happens if no bids?

---

### FINDING 16: `liquidityOfAndSync` — Permissionless State Modification
**Severity: INFORMATIONAL**
**Status: Safe but notable**

```solidity
function liquidityOfAndSync(address owner_) external returns (uint256 assets) {
    _syncInterests();  // STATE CHANGE: realizes pending interest
    assets = realisedLiquidityOf[owner_];
}
```

**Analysis:** ANY address can call this. It triggers `_syncInterests()` which:
- Increases `realisedDebt` (debtors owe more)
- Increases `realisedLiquidityOf[tranches]` (LPs earn interest)
- Updates `lastSyncedTimestamp`

**Not exploitable:** Interest accrual is time-based and inevitable. Calling it early just realizes it sooner. No one gains or loses from early sync.

**Gas griefing:** Attacker could call this every block to force interest calculation (expensive LogExpMath.pow). But this just costs the caller gas, not the protocol.

---

### FINDING 17: `maxDeposit` — Interest Calculation Without Sync
**Severity: INFORMATIONAL**
**Status: Conservative (safe)**

```solidity
function maxDeposit(address) public view override returns (uint256 maxAssets) {
    uint256 interests = lendingPool.calcUnrealisedDebt();  // view, no sync
    if (supplyCap > 0) {
        maxAssets = supplyCap - realisedLiquidity - interests;
    }
}
```

**Analysis:** Uses `calcUnrealisedDebt()` (view) to estimate current liquidity including pending interest. This is conservative — actual deposit will sync first (via `processInterests`), potentially showing slightly different numbers.

**Edge case:** If interest accrued between `maxDeposit()` call and actual `deposit()`, the deposit might slightly exceed the cap. But `depositInLendingPool` re-checks with synced values. Safe.

---

## UPDATED OVERALL ASSESSMENT

```
Security Score: 8.5/10 (unchanged)

Total findings: 17
  CRITICAL: 0
  HIGH:     0
  MEDIUM:   1 (Finding 14: vaultManagementAction trust boundary)
  LOW:      3 (Findings 2, 6, 15)
  INFO:     13

Key insight: The LendingPool is a well-designed accounting engine.
The REAL risk is in the contracts it TRUSTS:
  - Vault (health checks, action execution)
  - Liquidator (auction mechanics)
  - ActionHandler (external DeFi interactions)

Without vault-v2 and liquidator source, the full attack surface
cannot be assessed. The LendingPool alone is solid.
```

## NEXT STEPS FOR BOUNTY

```
Priority 1: Get vault-v2 source (private repo — need access or deployed bytecode)
Priority 2: Get liquidator source
Priority 3: Analyze ActionHandler integrations (swaps, deposits to external protocols)
Priority 4: Check deployed bytecode on Base for any deviations from source

If we can get the Vault bytecode from Base:
  cast code $VAULT_FACTORY --rpc-url $RPC
  → decompile → analyze vaultManagementAction
  → check health check logic
  → look for reentrancy via actionHandler callback
```

---

*Audited from source: arcadia-finance/arcadia-lending*
*LendingPool.sol (959) + Tranche.sol (382) + DebtToken.sol (214) + InterestRateModule.sol (108) + TrustedCreditor.sol (53) + Guardian.sol (207)*
*Total: 1,923 lines analyzed*
*BOZAGENTIC · "The core is solid. Hunt the edges."*
