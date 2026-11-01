# #58: Liquidation penalty should be taken from liquidator instead of from position.
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor disputed', 'sufficient quality report', ':robot:_24_group', 'duplicate-399']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L529-L531


# Vulnerability details


## Impact

Liquidation penalty should be taken from liquidator instead of from position.

## Bug Description

During liquidation, a liquidation penalty is taken from the liquidator. However, when calculating the amount of collateral the liquidator takes away, the liquidation penalty is still used for buying collateral. This essentially means that the penalty is not taken at all.

What's worse, the penalty is taken from the position, which increases the probability of having bad debt.

An example is:

1. There exists a position with 120 collateral, 108 debt. Liquidation ratio is 130%, liquidation discount is 90%, liquidation penalty is 5%. The position has not entered "bad debt", but since it is below liquidation ratio, it can be liquidated.
2. Liquidator comes and repays 108 debt, takes away `108/90% = 120` collateral. The repaid deltaDebt is `108*95% = 102.6`, and the penalty is `108*5% = 5.4`.
3. This means after liquidation, the collateral is gone, the bad debt is `108-102.6 = 5.4`.

The liquidator walked away with all collateral, and the penalty is payed by the position (which is really by the protocol since there is now bad debt).

The correct implementation should be that the penalty is taken from the liquidator, and that the liquidator would need to pay the extra 5%, which is:

1. Liquidator pays `108/95% = 113.68`
2. Repaid debt is `113.68*95% = 108`, making the debt to be fully repaid.
3. Liquidation penalty is `113.68*5% = 5.68`, which is send to lpETH stakers.


```solidity
    function liquidatePosition(address owner, uint256 repayAmount) external whenNotPaused {
        // validate params
        if (owner == address(0) || repayAmount == 0) revert CDPVault__liquidatePosition_invalidParameters();

        // load configs
        VaultConfig memory config = vaultConfig;
        LiquidationConfig memory liqConfig_ = liquidationConfig;

        // load liquidated position
        Position memory position = positions[owner];
        DebtData memory debtData = _calcDebt(position);

        // load price and calculate discounted price
        uint256 spotPrice_ = spotPrice();
        uint256 discountedPrice = wmul(spotPrice_, liqConfig_.liquidationDiscount);
        if (spotPrice_ == 0) revert CDPVault__liquidatePosition_invalidSpotPrice();
        // Enusure that there's no bad debt
        if (calcTotalDebt(debtData) > wmul(position.collateral, spotPrice_)) revert CDPVault__BadDebt();

        // compute collateral to take, debt to repay and penalty to pay
@>      uint256 takeCollateral = wdiv(repayAmount, discountedPrice);
@>      uint256 deltaDebt = wmul(repayAmount, liqConfig_.liquidationPenalty);
@>      uint256 penalty = wmul(repayAmount, WAD - liqConfig_.liquidationPenalty);
        if (takeCollateral > position.collateral) revert CDPVault__tooHighRepayAmount();

        // verify that the position is indeed unsafe
        if (_isCollateralized(calcTotalDebt(debtData), wmul(position.collateral, spotPrice_), config.liquidationRatio))
            revert CDPVault__liquidatePosition_notUnsafe();

        // transfer the repay amount from the liquidator to the vault
        poolUnderlying.safeTransferFrom(msg.sender, address(pool), repayAmount - penalty);

        uint256 newDebt;
        uint256 profit;
        uint256 maxRepayment = calcTotalDebt(debtData);
        uint256 newCumulativeIndex;
        if (deltaDebt == maxRepayment) {
            newDebt = 0;
            newCumulativeIndex = debtData.cumulativeIndexNow;
            profit = debtData.accruedInterest;
            position.cumulativeQuotaInterest = 0;
        } else {
            (newDebt, newCumulativeIndex, profit, position.cumulativeQuotaInterest) = calcDecrease(
                deltaDebt, // delta debt
                debtData.debt,
                debtData.cumulativeIndexNow, // current cumulative base interest index in Ray
                debtData.cumulativeIndexLastUpdate,
                debtData.cumulativeQuotaInterest
            );
        }
        position.cumulativeQuotaIndexLU = debtData.cumulativeQuotaIndexNow;
        // update liquidated position
        position = _modifyPosition(owner, position, newDebt, newCumulativeIndex, -toInt256(takeCollateral), totalDebt);

        pool.repayCreditAccount(debtData.debt - newDebt, profit, 0); // U:[CM-11]
        // transfer the collateral amount from the vault to the liquidator
        token.safeTransfer(msg.sender, takeCollateral);

        // Mint the penalty from the vault to the treasury
        poolUnderlying.safeTransferFrom(msg.sender, address(pool), penalty);
        IPoolV3Loop(address(pool)).mintProfit(penalty);

        if (debtData.debt - newDebt != 0) {
            IPoolV3(pool).updateQuotaRevenue(_calcQuotaRevenueChange(-int(debtData.debt - newDebt))); // U:[PQK-15]
        }
    }
```

## Proof of Concept

Presented above.

## Tools Used

Manual Review

## Recommended Mitigation Steps

```diff
-      uint256 takeCollateral = wdiv(repayAmount, discountedPrice);
-      uint256 deltaDebt = wmul(repayAmount, liqConfig_.liquidationPenalty);
-      uint256 penalty = wmul(repayAmount, WAD - liqConfig_.liquidationPenalty);
+      uint256 penalty = wmul(repayAmount, WAD - liqConfig_.liquidationPenalty);
+      uint256 repayAmount = wmul(repayAmount, liqConfig_.liquidationPenalty);
+      uint256 takeCollateral = wdiv(repayAmount, discountedPrice);
       ...

       // transfer the repay amount from the liquidator to the vault
-      poolUnderlying.safeTransferFrom(msg.sender, address(pool), repayAmount - penalty);
+      poolUnderlying.safeTransferFrom(msg.sender, address(pool), repayAmount);

```



## Assessed type

Other