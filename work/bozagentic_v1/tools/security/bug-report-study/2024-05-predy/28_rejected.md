# #28: Liquidators do not need to pay off bad debt when liquidating a portion of the position
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_primary', ':robot:_65_group', 'duplicate-189']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/main/src/libraries/logic/LiquidationLogic.sol#L62-L63


# Vulnerability details


## Impact

Liquidators do not need to pay off bad debt when liquidating a portion of the position. This will incentivize users to only liquidate 99.9999% of the vault and profiting from the better price, while leaving the bad debt to the last liquidator. And since there is no incentive to liquidate the last bit of the position, no one will perform the liquidation, which will always lead to bad debt for the protocol.

## Bug Description

Let's see how the liquidation process works:

1. The liquidator passes in a `closeRatio`, this is the percentage of the vault he wishes to liquidate.
2. The liquidator can perform a trade with a price he sets, as long as it is within the slippage limit. The liquidator benefits from this swap, since he can buy/sell baseToken lower/higher than the market price.
3. If `hasPosition == false`, and the remaining margin is positive, the margin is sent back to the recipient. However, if the remaining margin is negative, the last liquidator would need to pay off the bad debt.

The issue here is the liquidator can always just liquidate 99.9999% percentage of the position, and not paying for the bad debt at all. This would leave the bad debt for the last liquidator, which no one would want to be. Ultimately, the bad debt is left for the protocol.

Another scenario is that a user can open a position with high leverage (e.g. long baseToken with 10x leverage), if it turns insolvent, he can simply liquidate himself, and sell the token at a higher price (may be even higher than when he longed the token), and leaving the bad debt to the protocol.

```solidity
    function liquidate(
        uint256 vaultId,
>       uint256 closeRatio,
        GlobalDataLibrary.GlobalData storage globalData,
        bytes memory settlementData
    ) external returns (IPredyPool.TradeResult memory tradeResult) {
        require(closeRatio > 0 && closeRatio <= 1e18, "ICR");
        DataType.Vault storage vault = globalData.vaults[vaultId];
        DataType.PairStatus storage pairStatus = globalData.pairs[vault.openPosition.pairId];

        // update interest growth
        ApplyInterestLib.applyInterestForToken(globalData.pairs, vault.openPosition.pairId);

        // update rebalance interest growth
        Perp.updateRebalanceInterestGrowth(pairStatus, pairStatus.sqrtAssetStatus);

        // Checks the vault is danger
        (uint256 sqrtOraclePrice, uint256 slippageTolerance) =
            checkVaultIsDanger(pairStatus, vault, globalData.rebalanceFeeGrowthCache);

        IPredyPool.TradeParams memory tradeParams = IPredyPool.TradeParams(
            vault.openPosition.pairId,
            vaultId,
>           -vault.openPosition.perp.amount * int256(closeRatio) / 1e18,
>           -vault.openPosition.sqrtPerp.amount * int256(closeRatio) / 1e18,
            ""
        );

        tradeResult = Trade.trade(globalData, tradeParams, settlementData);

        vault.margin += tradeResult.fee + tradeResult.payoff.perpPayoff + tradeResult.payoff.sqrtPayoff;

        tradeResult.sqrtTwap = sqrtOraclePrice;

        bool hasPosition;

        (tradeResult.minMargin,, hasPosition,) =
            PositionCalculator.calculateMinMargin(pairStatus, vault, DataType.FeeAmount(0, 0));

        // Check if the price is within the slippage tolerance range to ensure that the price does not become
        // excessively favorable to the liquidator.
>       SlippageLib.checkPrice(
            sqrtOraclePrice,
            tradeResult,
            slippageTolerance,
            tradeParams.tradeAmountSqrt == 0 ? 0 : _MAX_ACCEPTABLE_SQRT_PRICE_RANGE
        );

        uint256 sentMarginAmount = 0;

>       if (!hasPosition) {
            int256 remainingMargin = vault.margin;

            if (remainingMargin > 0) {
                if (vault.recipient != address(0)) {
                    // Send the remaining margin to the recipient.
                    vault.margin = 0;

                    sentMarginAmount = uint256(remainingMargin);

                    ERC20(pairStatus.quotePool.token).safeTransfer(vault.recipient, sentMarginAmount);
                }
            } else if (remainingMargin < 0) {
                vault.margin = 0;

                // To prevent the liquidator from unfairly profiting through arbitrage trades in the AMM and passing losses onto the protocol,
                // any losses that cannot be covered by the vault must be compensated by the liquidator
                ERC20(pairStatus.quotePool.token).safeTransferFrom(msg.sender, address(this), uint256(-remainingMargin));
            }
        }
    }
```

## Proof of Concept

Presented above.

## Tools Used

Manual review

## Recommended Mitigation Steps

Remove the `closeRatio`, and only allow liquidating the entire vault position.


## Assessed type

Other