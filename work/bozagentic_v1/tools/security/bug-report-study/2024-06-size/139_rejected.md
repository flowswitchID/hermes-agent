# #139: `Liquidate.executeLiquidate()` calculates `liquidatorReward` incorrectly.
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_09_group', 'duplicate-21']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Liquidate.sol#L98


# Vulnerability details

## Impact
1. If a liquidator sets a proper `minimumCollateralProfit`, `executeLiquidate()` would revert and unhealthy debts wouldn't be liquidated in time.
2. Otherwise, a liquidator would receive less rewards(almost zero).

## Proof of Concept
While executing a liquidation, it calculates `liquidatorReward` with `feeConfig.liquidationRewardPercent`.

```solidity
File: Liquidate.sol
095:         if (assignedCollateral > debtInCollateralToken) {
096:             uint256 liquidatorReward = Math.min(
097:                 assignedCollateral - debtInCollateralToken,
098:                 Math.mulDivUp(debtPosition.futureValue, state.feeConfig.liquidationRewardPercent, PERCENT) //@audit wrong token amount
099:             );
100:             liquidatorProfitCollateralToken = debtInCollateralToken + liquidatorReward;
```

But it applies `liquidationRewardPercent` to [debtPosition.futureValue](https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Liquidate.sol#L98) which shows a debt token amount.

`assignedCollateral - debtInCollateralToken` means a collateral amount of 18 decimals and `debtPosition.futureValue` means a debt amount of the borrow token decimals(currently 6).

So `liquidatorReward` will be less than expected due to the low decimals.

## Tools Used
Manual Review

## Recommended Mitigation Steps
It should use `debtInCollateralToken` instead of `debtPosition.futureValue`.

```diff
    uint256 assignedCollateral = state.getDebtPositionAssignedCollateral(debtPosition);
    uint256 debtInCollateralToken = state.debtTokenAmountToCollateralTokenAmount(debtPosition.futureValue);
    uint256 protocolProfitCollateralToken = 0;

    if (assignedCollateral > debtInCollateralToken) {
        uint256 liquidatorReward = Math.min(
        assignedCollateral - debtInCollateralToken,
-            Math.mulDivUp(debtPosition.futureValue, state.feeConfig.liquidationRewardPercent, PERCENT)
+            Math.mulDivUp(debtInCollateralToken, state.feeConfig.liquidationRewardPercent, PERCENT)
    );
```


## Assessed type

Decimal