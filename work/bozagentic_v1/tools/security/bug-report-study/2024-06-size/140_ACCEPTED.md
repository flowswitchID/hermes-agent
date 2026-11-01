# #140: `Liquidate.executeLiquidate()` calculates `collateralRemainderCap` incorrectly.
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', ':robot:_83_group', 'duplicate-70']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Liquidate.sol#L108


# Vulnerability details

## Impact
During liquidation, the protocol would charge more funds than expected from non-underwater overdue loans. 
It means the owners of non-underwater overdue loans might lose funds unfairly.

## Proof of Concept
In `executeLiquidate()`, it charges a protocol profit from the remaining collateral.

```solidity
    if (assignedCollateral > debtInCollateralToken) {
        uint256 liquidatorReward = Math.min(
        assignedCollateral - debtInCollateralToken,
        Math.mulDivUp(debtPosition.futureValue, state.feeConfig.liquidationRewardPercent, PERCENT)
        );
        liquidatorProfitCollateralToken = debtInCollateralToken + liquidatorReward;

        // split the remaining collateral between the protocol and the borrower, capped by the crLiquidation
        uint256 collateralRemainder = assignedCollateral - liquidatorProfitCollateralToken;

        // cap the collateral remainder to the liquidation collateral ratio
        //   otherwise, the split for non-underwater overdue loans could be too much
        uint256 collateralRemainderCap =
        Math.mulDivDown(debtInCollateralToken, state.riskConfig.crLiquidation, PERCENT); //@audit wrong cap

        collateralRemainder = Math.min(collateralRemainder, collateralRemainderCap);

        protocolProfitCollateralToken = Math.mulDivDown(collateralRemainder, collateralProtocolPercent, PERCENT);
    }
```

As we can see from the comments, it applies a collateral remainder cap for non-underwater overdue loans but the calculation is wrong.

- We assume `crLiquidation = 130%, liquidationRewardPercent = 5%, overdueCollateralProtocolPercent = 1%, debtInCollateralToken = 100, assignedCollateral = 200.`
- While liquidating this non-underwater overdue loan, `liquidatorReward = min(200 - 100, 100 * 5%) = 5`.
- So `collateralRemainder = 200 - 100 - 5 = 95` and `collateralRemainderCap = 100 * 130% = 130`.
- As a result, `protocolProfitCollateralToken = min(95, 130) * 1% = 0.95` will be charged as a protocol profit.(This is wrong)
- The protocol profit should be `(collateralRemainderCap - liquidatorProfitCollateralToken) * overdueCollateralProtocolPercent = (130 - 105) * 1% = 0.25`.

The original intention of `collateralRemainderCap` is to charge protocol rewards for 130% of `debtInCollateralToken`. But it works incorrectly because it compares with `collateralRemainder` which `debtInCollateralToken` is deducted from already.

## Tools Used
Manual Review

## Recommended Mitigation Steps
Recommend fixing like this.

```diff
        // split the remaining collateral between the protocol and the borrower, capped by the crLiquidation
        uint256 collateralRemainder = assignedCollateral - liquidatorProfitCollateralToken;

        // cap the collateral remainder to the liquidation collateral ratio
        //   otherwise, the split for non-underwater overdue loans could be too much
        uint256 collateralRemainderCap =
        Math.mulDivDown(debtInCollateralToken, state.riskConfig.crLiquidation, PERCENT);

+       collateralRemainderCap = collateralRemainderCap - Math.min(collateralRemainderCap, liquidatorProfitCollateralToken) //deducts liquidatorProfitCollateralToken like collateralRemainder

        collateralRemainder = Math.min(collateralRemainder, collateralRemainderCap);

        protocolProfitCollateralToken = Math.mulDivDown(collateralRemainder, collateralProtocolPercent, PERCENT);
```


## Assessed type

Math