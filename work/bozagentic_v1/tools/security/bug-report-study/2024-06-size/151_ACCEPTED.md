# #151: Unfair calculation logic of protocol profit during liquidation
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_83_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Liquidate.sol#L112


# Vulnerability details

## Impact
During liquidation, the higher the collateral ratio the borrower has, the more funds would be deducted as a protocol profit.

## Proof of Concept
During liquidation in `executeLiquidate`, it charges a protocol profit.

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
        Math.mulDivDown(debtInCollateralToken, state.riskConfig.crLiquidation, PERCENT);

        collateralRemainder = Math.min(collateralRemainder, collateralRemainderCap);

        protocolProfitCollateralToken = Math.mulDivDown(collateralRemainder, collateralProtocolPercent, PERCENT); //@audit looks unfair
 }
```

It charges `collateralProtocolPercent` of `collateralRemainder` but it looks unfair as shown in the below example.

- There are 2 borrowers Alice and Bob. Both of them have the same debts and Alice's `collateralRatio = 120%`. Bob's `collateralRatio = 110%`.
- We assume `crLiquidation = 130%, collateralProtocolPercent = 10%, liquidationRewardPercent = 5%`.
- For Alice, `debtInCollateralToken = 100, assignedCollateral = 120, liquidatorReward = min(120 - 100, 100 * 5%) = 5, collateralRemainder = 120 - 100 - 5 = 15`. So `protocolProfitCollateralToken = 15 * 10% = 1.5` will be charged.
- For Bob, `debtInCollateralToken = 100, assignedCollateral = 110, liquidatorReward = min(110 - 100, 100 * 5%) = 5, collateralRemainder = 110 - 100 - 5 = 5`. So `protocolProfitCollateralToken = 5 * 10% = 0.5` will be charged.

But we can say Alice's debt position is less serious than Bob's(due to the higher collateral ratio) and it's unfair to charge more funds from her just because she has more free collaterals after the liquidation.

At least, we should charge the same protocol profits for Alice and Bob.

Here is another weird example.
- With the above config params, Alice pays 1.5 as a protocol profit during the liquidation.
- But Alice has increased her collateral ratio a little(120% to 125%, still liquidatable) before the liquidation to make herself healthier.
- During the liquidation, `debtInCollateralToken = 100, assignedCollateral = 125, liquidatorReward = min(125 - 100, 100 * 5%) = 5, collateralRemainder = 125 - 100 - 5 = 20, protocolProfitCollateralToken = 20 * 10% = 2`
- So she just loses more funds after making herself healthier.

## Tools Used
Manual Review

## Recommended Mitigation Steps
We should calculate the `protocolProfitCollateralToken` as a `collateralProtocolPercent` of `debtInCollateralToken`, not `collateralRemainder`.

```diff
 collateralRemainder = Math.min(collateralRemainder, collateralRemainderCap);

-    protocolProfitCollateralToken = Math.mulDivDown(collateralRemainder, collateralProtocolPercent, PERCENT);

+    protocolProfitCollateralToken = Math.min(collateralRemainder, Math.mulDivDown(debtInCollateralToken, collateralProtocolPercent, PERCENT));
```


## Assessed type

Other