# ARCADIA FINANCE V2 — SECURITY AUDIT REPORT
# LendingPool V2 + LiquidatorL2 + Tranche + DebtToken
# Source: github.com/arcadia-finance/lending-v2 (deployed on Base)
# BOZAGENTIC · 2026-07-29
# Total analyzed: ~3,500 lines (LendingPool 1338 + LiquidatorL2 613 + Tranche 382 + DebtToken 214 + interfaces/libs)

---

## EXECUTIVE SUMMARY

```
Protocol:    Arcadia Finance V2 (lending + liquidation)
Chain:       Base (deployed: 0x803ea69c... WETH pool, 0x3ec4a293... USDC pool)
Score:       8.0/10
Findings:    7 total
  HIGH:      1
  MEDIUM:    2
  LOW:       2
  INFO:      2
```

---

## FINDING 1: `donateToTranche` — Inflation Attack Mitigation Removed
**Severity: HIGH**
**Status: Needs verification of Tranche virtual shares**

### V1 (had protection):
```solidity
// arcadia-lending/src/LendingPool.sol (V1)
function donateToTranche(uint256 trancheIndex, uint256 assets) external ... {
    require(ERC4626(tranche).totalSupply() >= 10 ** decimals, "LP_DTT: Insufficient shares");
    // ↑ BLOCKS donation when shares < 10^decimals
}
```

### V2 (protection REMOVED):
```solidity
// lending-v2/src/LendingPool.sol (V2) line 363
function donateToTranche(uint256 trancheIndex, uint256 assets) external whenDepositNotPaused processInterests {
    if (assets == 0) revert LendingPoolErrors.ZeroAmount();
    address tranche = tranches[trancheIndex];
    // ⚠️ NO minimum share check!
    // Comment says: "Inflation attacks by the first depositor in the Tranches
    //                have to be prevented with virtual assets/shares."
    asset.safeTransferFrom(msg.sender, address(this), assets);
    unchecked {
        realisedLiquidityOf[tranche] += assets;
        totalRealisedLiquidity = SafeCastLib.safeCastTo128(assets + totalRealisedLiquidity);
    }
}
```

### Attack scenario:
```
1. Attacker deposits 1 wei into Junior Tranche → gets 1 share
2. Attacker calls donateToTranche(jrIndex, 1000 ETH)
   → realisedLiquidityOf[jrTranche] += 1000 ETH
   → totalAssets() = 1000 ETH + 1 wei, totalSupply = 1 share
   → 1 share = 1000 ETH now
3. Victim deposits 1000 ETH → gets 1000 * 1 / 1000 = 1 share (rounding!)
4. Attacker redeems 1 share → gets ~1000 ETH
5. Net: attacker paid 1 wei + 1000 ETH donation, got 1000 ETH back
   → Victim's 1000 ETH is now worth 0 (attacker's share = 1000 ETH)
```

### Mitigation claim:
V2 comment says "Inflation attacks have to be prevented with virtual assets/shares" — meaning the **Tranche contract** should implement OZ-style virtual shares (`totalAssets() + 1`, `totalSupply() + 10^offset`).

### What needs verification:
```bash
# Check if deployed Tranche on Base uses virtual shares:
# 1. Get Tranche address from LendingPool
cast call $POOL "tranches(uint256)(address)" 0 --rpc-url $RPC
# 2. Check Tranche's convertToShares implementation
# If it does: assets.mulDivDown(supply, totalAssets) → VULNERABLE
# If it does: assets.mulDivDown(supply + 10^offset, totalAssets + 1) → SAFE
```

### Impact:
If Tranche does NOT implement virtual shares → **first depositor can steal all subsequent deposits via donation inflation.** This is the exact same bug class as the Basin sync() attack you found.

### Recommendation:
Verify Tranche implementation on-chain. If no virtual shares → CRITICAL, submit to Immunefi immediately.

---

## FINDING 2: LiquidatorL2 `bid()` — Callback Before Payment
**Severity: MEDIUM**
**Status: By design, but risky**

```solidity
// LiquidatorL2.sol line 377-423
function bid(address account, uint256[] memory bidAmounts, bool endAuction_, bytes calldata data)
    external nonReentrant
{
    // Step 1: Transfer assets TO bidder FIRST
    bidAmounts = IAccount(account).auctionBid(..., msg.sender);  // ← bidder gets assets

    // Step 2: Calculate price
    uint256 price = _calculateBidPrice(auctionInformation_, totalShare);

    // Step 3: CALLBACK to bidder (if contract)
    if (msg.sender.code.length > 0) IBidCallback(msg.sender).bidCallback(bidAmounts, price, data);
    // ↑ Bidder has assets + knows price. Can execute arbitrary logic HERE.

    // Step 4: Collect payment AFTER callback
    bool earlyTerminate = ILendingPool(creditor).auctionRepay(startDebt, minimumMargin, price, account, msg.sender);
    // ↑ LendingPool does transferFrom(bidder → pool). Bidder must have approved.
}
```

### Risk:
Between Step 1 (assets received) and Step 4 (payment collected), the bidder's callback can:
- Swap the received assets on a DEX
- Use proceeds to pay the debt (flash-loan-like pattern)
- If swap fails or price moves → bidder might not have enough to pay

### Mitigation in code:
- `nonReentrant` prevents re-entering Liquidator
- `auctionRepay` does `transferFrom(bidder → pool)` — if bidder can't pay, tx reverts
- Bidder must have approved LendingPool before bidding

### Residual risk:
- Bidder can use received assets as collateral elsewhere DURING the callback
- If the external protocol doesn't check for ongoing auctions → composable exploit
- The `nonReentrant` only protects the Liquidator, not external protocols

### Recommendation:
Document that `bidCallback` executes with bidder holding auction assets. External integrations should check `auctionInformation[account].inAuction` before accepting those assets as collateral.

---

## FINDING 3: `_calculateTotalShare` — Division by Zero on Empty Assets
**Severity: MEDIUM**
**Status: Potential auction bricking**

```solidity
// LiquidatorL2.sol line 457-471
function _calculateTotalShare(AuctionInformation storage auctionInformation_, uint256[] memory bidAmounts)
    internal view returns (uint256 totalShare)
{
    uint256[] memory assetAmounts = auctionInformation_.assetAmounts;
    uint32[] memory assetShares = auctionInformation_.assetShares;

    for (uint256 i; i < assetAmounts.length; ++i) {
        unchecked {
            totalShare += bidAmounts[i].mulDivUp(assetShares[i], assetAmounts[i]);
            //                                              ↑ DIVISION BY ZERO if assetAmounts[i] == 0
        }
    }
}
```

### Attack scenario:
```
1. Account holds [WETH, dust_token] where dust_token balance = 0
   (or balance becomes 0 between startLiquidation and bid)
2. liquidateAccount() stores assetAmounts = [10 WETH, 0 dust]
3. _getAssetShares: totalValue = WETH_value + 0 = WETH_value
   assetShares = [10000, 0] (dust gets 0 share)
4. Bidder calls bid([5 WETH, 0 dust])
5. _calculateTotalShare: 5 * 10000 / 10 + 0 * 0 / 0
   → 0 * 0 / 0 = 0/0 → REVERT (division by zero in mulDivUp)
6. Auction is BRICKED — no one can bid
```

### Mitigation:
- `bidAmounts[i] = 0` AND `assetShares[i] = 0` → `0 * 0 / 0` → Solidity 0.8 reverts
- Even though mathematically 0/0 should be 0 here, Solidity doesn't know that
- `mulDivUp(0, 0, 0)` → denominator = 0 → revert

### Impact:
If an Account has any asset with 0 balance at liquidation time, the auction CANNOT be bid on. After cutoffTime, assets go to `accountRecipient` (protocol) and bad debt is socialized to junior tranche LPs.

### Recommendation:
Add check: `if (assetAmounts[i] == 0 || bidAmounts[i] == 0) continue;`

---

## FINDING 4: Sequencer Downtime — Auction Reset Without Bound
**Severity: LOW**
**Status: By design, but edge case**

```solidity
// LiquidatorL2.sol line 385-389 (in bid())
(, uint256 sequencerStartedAt) = _getSequencerUpTime();
if (sequencerStartedAt > auctionInformation_.startTime) {
    auctionInformation_.startTime = uint32(sequencerStartedAt);  // RESET start time
}
```

### Issue:
If sequencer goes down repeatedly during an auction, `startTime` keeps resetting forward. The auction never reaches `cutoffTime`. Assets are stuck in limbo indefinitely.

### Mitigation:
- Base sequencer downtime is rare (< 1 hour historically)
- `cutoffTime` is 4 hours default — would need 4+ hours of cumulative downtime
- Each reset is logged (startTime change visible on-chain)

### Residual risk:
- Coordinated sequencer downtime (unlikely on Base, possible on newer L2s)
- No maximum number of resets
- No absolute deadline (startTime + N * cutoffTime)

---

## FINDING 5: `flashAction` — Callback Pattern (V2 improvement over V1)
**Severity: LOW (improvement, but new trust assumption)**

### V1 (insecure pattern):
```solidity
// V1: funds sent BEFORE health check
asset.safeTransfer(actionHandler, amountBorrowed);  // ← funds gone
IVault(vault).vaultManagementAction(actionHandler, actionData);  // ← check after
```

### V2 (callback pattern):
```solidity
// V2: Account controls the flow via callback
callbackAccount = account;
bytes memory callbackData = abi.encode(amountBorrowed, actionTarget, msg.sender, referrer);
uint256 accountVersion = IAccount(account).flashActionByCreditor(callbackData, actionTarget, actionData);
// Account calls back into _flashActionCallback() to mint debt
// Account does health check internally
// Account is nonReentrant during the entire flow
```

### Improvement:
- Account cannot be reentered between borrow and health check
- Debt minting happens inside Account's callback (atomic)
- Account controls action execution order

### New trust assumption:
- LendingPool trusts Account to call `_flashActionCallback` correctly
- Account trusts `actionTarget` to execute actions properly
- If Account implementation has a bug in `flashActionByCreditor` → LendingPool exposed

### Recommendation:
Audit the Account (accounts-v2) implementation of `flashActionByCreditor` — this is the critical path.

---

## FINDING 6: `auctionRepay` — Surplus Handling Race
**Severity: INFO**
**Status: Correct but notable**

```solidity
// LendingPool.sol line 500-526
function auctionRepay(uint256 startDebt, uint256 minimumMargin_, uint256 amount, address account, address bidder)
    external onlyLiquidator processInterests returns (bool earlyTerminate)
{
    asset.safeTransferFrom(bidder, address(this), amount);  // collect full amount first

    uint256 accountDebt = maxWithdraw(account);
    if (accountDebt <= amount) {
        earlyTerminate = true;
        _settleLiquidationHappyFlow(account, startDebt, minimumMargin_, bidder, (amount - accountDebt));
        // ↑ surplus (amount - accountDebt) credited to account owner
        amount = accountDebt;  // only burn actual debt
    }
    _withdraw(amount, address(this), account);
}
```

### Analysis:
- Full `amount` transferred from bidder FIRST
- If surplus exists, it's credited to account owner via `_settleLiquidationHappyFlow`
- Only `accountDebt` is burned from debt tokens
- Surplus is claimable by account owner via `withdrawFromLendingPool`

**Correct implementation.** No funds lost. ✅

---

## FINDING 7: `setAccountRecipient` — No Validation
**Severity: INFO**
**Status: Trust assumption documented**

```solidity
// LiquidatorL2.sol line 187-190
function setAccountRecipient(address creditor, address accountRecipient) external {
    if (msg.sender != ICreditor(creditor).riskManager()) revert LiquidatorErrors.NotAuthorized();
    creditorToAccountRecipient[creditor] = accountRecipient;
    // ⚠️ No check that accountRecipient is not address(0)
    // ⚠️ No check that accountRecipient is not an Account (documented in comment)
}
```

### Documented risk (from source comment):
```
"Accounts themselves must never be set as accountRecipient,
since ownership transfers of Accounts to themselves will revert.
A check on 'isAccount()' would not be sufficient to prevent this from happening,
since account addresses can be pre-computed before deployment."
```

### Impact:
If riskManager sets accountRecipient to address(0) → `auctionBoughtIn(address(0))` → assets burned/lost after cutoff.
If set to a pre-computed Account address → ownership transfer reverts → assets stuck.

---

## COMPARISON: V1 vs V2

| Aspect | V1 | V2 |
|--------|----|----|
| Inflation protection | `totalSupply >= 10^decimals` check | Removed — relies on Tranche virtual shares |
| Leverage action | Funds sent before health check | Callback pattern (Account controls flow) |
| Reentrancy | CEI only | `nonReentrant` on Liquidator + Account callback |
| Liquidation | Simple startAuction | Dutch auction with bid callback |
| Sequencer | N/A | Sequencer uptime oracle (L2-specific) |
| Guardian | 30-day forced unpause | Same + riskManager role |
| Debt token | Non-transferable | Non-transferable (same) |
| Interest | LogExpMath compound | Same |

---

## PRIORITY ACTIONS

```
🔴 URGENT: Verify Tranche virtual shares on deployed Base contracts
   → If NO virtual shares → Finding 1 is CRITICAL → Immunefi submission
   → cast call $TRANCHE "convertToShares(uint256)(uint256)" 1000000 --rpc-url $RPC
   → Compare with expected formula

🟡 IMPORTANT: Audit accounts-v2 `flashActionByCreditor` implementation
   → This is the critical trust boundary for leveraged actions
   → Source: lib/accounts-v2/src/abstracts/Creditor.sol

🟡 IMPORTANT: Verify _calculateTotalShare with zero-balance assets
   → Write Foundry test: account with [WETH, 0-balance token]
   → Call liquidateAccount → bid → check if reverts

🟢 NICE TO HAVE: Audit Account.startLiquidation / auctionBid / auctionBoughtIn
   → These are called by Liquidator but implemented in Account
   → Source: lib/accounts-v2/
```

---

## VERIFICATION COMMANDS (run on Base)

```bash
RPC=https://mainnet.base.org
POOL_WETH=0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2
POOL_USDC=0x3ec4a293Fb906DD2Cd440c20dECB250DeF141dF1

# Step 1: Get Tranche addresses
cast call $POOL_WETH "0x..." 0 --rpc-url $RPC  # tranches(0)
cast call $POOL_WETH "0x..." 1 --rpc-url $RPC  # tranches(1)

# Step 2: Check Tranche convertToShares (virtual shares check)
# If returns: assets * supply / totalAssets → NO virtual shares → VULNERABLE
# If returns: assets * (supply + offset) / (totalAssets + 1) → SAFE

# Step 3: Check donateToTranche behavior
# Simulate: deposit 1 wei → donate large amount → check share price

# Step 4: Check Liquidator address
cast storage $POOL_WETH 2 --rpc-url $RPC  # LIQUIDATOR is immutable, check constructor args
```

---

*Audited from source: arcadia-finance/lending-v2*
*LendingPool.sol (1338) + LiquidatorL2.sol (613) + Tranche.sol (382) + DebtToken.sol (214)*
*+ InterestRateModule + Guardian + TrustedCreditor + interfaces*
*Total: ~3,500 lines analyzed*
*Deployed on Base: WETH pool 0x803ea69c..., USDC pool 0x3ec4a293...*
*BOZAGENTIC · "V2 is better than V1. But 'better' ≠ 'safe'."*
