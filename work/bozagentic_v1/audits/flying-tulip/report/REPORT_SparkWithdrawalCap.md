# Spark Savings Vault Withdrawal Caps Lock 35-48% of PUT Collateral

## Summary

The USDC and wETH yield strategies were changed from AaveStrategy (as documented) to Spark Savings ERC4626 vaults (spUSDC, spETH) without updating documentation or KNOWN_ISSUES.md. Spark Savings vaults deploy the majority of assets to MakerDAO's DSR (Dai Savings Rate), leaving only a fraction as liquid USDC/WETH. The vault's `maxWithdraw()` is capped at the liquid balance, meaning **35.22% of USDC PUT collateral ($5.43M) and 47.82% of wETH PUT collateral (2,291 ETH) are currently NOT withdrawable**. In a bank run scenario where all PUT holders divest simultaneously, 35-48% of users **cannot exit their positions** — `divest()` reverts with `ftYieldWrapperInsufficientLiquidity`.

## Vulnerability Detail

### Root Cause

1. **Strategies were changed from Aave to Spark without disclosure:**
   - Docs reference AaveStrategy addresses: USDC `0x0987...`, wETH `0x2e43...`
   - Actual deployed strategies: USDC `0xCFb9...` (Spark spUSDC), wETH `0x3f53...` (Spark spETH)
   - These are ERC4626 vaults, NOT AaveStrategy contracts (no `aToken()`, no `pool()`)

2. **Spark Savings vaults deploy to DSR:**
   - spUSDC vault: `totalAssets = $268.6M`, but liquid USDC = `$9.99M` (only 3.7% liquid)
   - `maxWithdraw(strategy)` = vault's liquid USDC balance = `$9.99M`
   - Strategy's full position value = `$15.42M`
   - **Gap: $5.43M (35.22%) is locked in DSR with no guaranteed withdrawal timeline**

3. **Wrapper correctly reports the limit, but the limit IS the problem:**
   - `wrapper.availableToWithdraw()` = `$9.99M` (correctly reflects vault cap)
   - `PM.collateralSupply(USDC)` = `$15.42M` (total collateral backing active PUTs)
   - `collateralSupply > availableToWithdraw` → **not all PUT holders can divest**

### Revert Path

```
User calls PutManager.divest(id, ftAmount)
  → collateralFromFT() computes _capitalDivesting
  → wrapper.withdraw(_capitalDivesting, user)
    → idle = token.balanceOf(wrapper) = 0
    → strategy.withdraw(remaining)
      → vault.redeem/withdraw(amount)
        → amount > maxWithdraw → REVERT
      → strategy: received != amount → revert StrategyInsufficientLiquidity
    → wrapper: catch → continue → remaining != 0
    → revert ftYieldWrapperInsufficientLiquidity()
  → divest() REVERTS (atomic rollback)
  → USER CANNOT EXIT PUT POSITION
```

### On-Chain Evidence (Ethereum mainnet)

| Token | Strategy Type | PUT Collateral | Available to Withdraw | Shortfall | Locked % |
|-------|--------------|----------------|----------------------|-----------|----------|
| USDC  | Spark (spUSDC) | $15.42M | $9.99M | **$5.43M** | **35.22%** |
| wETH  | Spark (spETH) | 4,792 ETH | 2,500 ETH | **2,291 ETH** | **47.82%** |
| USDT  | Spark (spUSDT) | $17.23M | $17.23M | $0 | 0% ✅ |
| USDS  | Aave | $2.38B | $2.38B | $0 | 0% ✅ |
| USDTb | Aave | $109.8M | $109.8M | $0 | 0% ✅ |
| USDe  | Aave | $70.9B | $70.9B | $0 | 0% ✅ |

### Griefing / First-Come-First-Served Race

During market stress (when users MOST want to exit):
1. News breaks → all PUT holders attempt to divest
2. First users drain vault liquidity ($9.99M USDC / 2,500 ETH)
3. Later users' `divest()` **REVERTS** — they are stuck
4. No guaranteed timeline for DSR to release funds
5. Users must repeatedly retry, competing for limited liquidity

## Impact

- **$5.43M USDC collateral** (35.22%) is not withdrawable on demand
- **2,291 wETH collateral** (47.82%) is not withdrawable on demand
- In a bank run, 35-48% of USDC/wETH PUT holders **cannot exit their positions**
- The Perpetual PUT's core value proposition ("Exit at par whenever you choose") is broken for these tokens
- Users who don't check `canDivest()`/`maxDivestable()` get unexpected reverts
- No timeline guarantee for when locked funds become available
- Documentation still references Aave strategies — users are unaware of the change

## Code Snippet

```solidity
// PutManager.divest() — line 518-538
function divest(uint256 id, uint256 amount_ft) external nonReentrant {
    (address token,,,,,, uint256 strike,, uint64 ftPerUSD) = pFT.puts(id);
    uint256 _capitalDivesting = collateralFromFT(amount_ft, strike, collateralDecimals[token], ftPerUSD);
    // ...
    IftYieldWrapper _vault = IftYieldWrapper(vaults[token]);
    _vault.withdraw(_capitalDivesting, msg.sender);  // ← REVERTS if > maxWithdraw
}

// ftYieldWrapper.withdraw() — line 483-575
function withdraw(uint256 amount, address to) external nonReentrant onlyPutManagerOrDepositor {
    // ...
    for (uint256 i = 0; i < _strategiesLength && remaining != 0; i++) {
        try strategies[i].withdraw(toRequest) returns (uint256 received) {
            // Spark strategy: vault.maxWithdraw caps the amount
            // If vault reverts → catch → continue → remaining stays > 0
        } catch { continue; }
    }
    if (remaining != 0) {
        revert ftYieldWrapperInsufficientLiquidity();  // ← USER STUCK
    }
}
```

## Tool Used

Foundry fork test against Ethereum mainnet (8 proofs, all passing):

```
forge test --match-contract SparkWithdrawalCapPoC -vvv --fork-url <ETH_RPC>

[PASS] test_proof1_strategies_changed()     — Strategies differ from docs
[PASS] test_proof2_usdc_cap()               — USDC maxWithdraw < full position
[PASS] test_proof3_weth_cap()               — wETH maxWithdraw < full position
[PASS] test_proof4_usdc_bank_run()          — USDC collateralSupply > available
[PASS] test_proof5_weth_bank_run()          — wETH collateralSupply > available
[PASS] test_proof6_canWithdraw_false()      — canWithdraw(full) returns false
[PASS] test_proof7_aave_liquid()            — Aave strategies fully liquid (contrast)
[PASS] test_proof8_dsr_root_cause()         — maxWithdraw == liquid balance (DSR holds rest)
```

## Recommendation

1. **Immediate:** Update documentation to reflect actual Spark strategies (not Aave)
2. **Immediate:** Add to KNOWN_ISSUES.md that USDC/wETH have withdrawal caps
3. **Short-term:** Add a `maxDivestable()` check in the UI to warn users before submitting
4. **Medium-term:** Consider maintaining a liquid buffer in the wrapper (idle tokens) to cover a percentage of collateralSupply beyond vault's maxWithdraw
5. **Medium-term:** Evaluate whether Spark Savings vaults are appropriate for PUT collateral that promises "Exit at par whenever you choose"
6. **Long-term:** Consider diversifying strategies (e.g., keep a portion in Aave for instant liquidity) or implementing a withdrawal queue for large divestments

## Distinction from Known Issue AAVE-01

| | AAVE-01 | This Finding |
|---|---------|-------------|
| **Title** | availableToWithdraw doesn't check pool reserves | Spark vault withdrawal caps lock 35-48% of collateral |
| **Strategy** | AaveStrategy on Aave V3 | Spark Savings ERC4626 vaults (spUSDC, spETH) |
| **Root cause** | Aave pool might not have enough underlying | Spark deploys to DSR, explicit maxWithdraw cap |
| **Status** | Theoretical (Aave usually liquid) | **ACTUAL** — 35-48% currently locked on-chain |
| **Mitigation** | try/catch in wrapper | try/catch catches revert but user STILL can't divest |
| **Docs** | References Aave strategies | Strategies CHANGED to Spark, docs NOT updated |
