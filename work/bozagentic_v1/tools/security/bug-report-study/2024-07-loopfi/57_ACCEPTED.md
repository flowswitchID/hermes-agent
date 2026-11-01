# #57: `CDPVault.sol#liquidatePositionBadDebt()` should not set profit = 0 when calling `pool.repayCreditAccount()`.
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', ':robot:_primary', ':robot:_86_group', 'H-12']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/main/src/CDPVault.sol#L624
https://github.com/code-423n4/2024-07-loopfi/blob/main/src/PoolV3.sol#L529-L576


# Vulnerability details


## Impact

`CDPVault.sol#liquidatePositionBadDebt()` should not set profit = 0 when calling `pool.repayCreditAccount()`. This would cause a loss of funds to lpETH stakers.

## Bug Description

First we need to understand how `liquidatePositionBadDebt()` works. When there is a bad debt detected for a position, any liquidator can come and liquidate the position. The liquidator is required to buy ALL the collateral at a discount price, and the loss (totalDebt - repayAmount) is sent to PoolV3 to be beared by the lpETH stakers.

This is all good, but the issue here is that when the liquidator repays the debt, it is compared against the totalDebt of the position, which includes the interest. This interest should also be sent to the lpETH stakers, but is currently not, which would result in loss of funds for the lpETH stakers.

An example:

1. CDPVault position has debt principal == 1000, debt interest == 500. Total debt == 1500. Collateral value == 1600, discount == 90%, discount value == 1440.
2. Liquidator comes and pay off 1440, loss is 1500-1440 = 60, so `pool.repayCreditAccount(1000, 0, 60)` is called.
3. The loss is 60, and the same amount of lpETH is burned from the StakingLPEth contract.

However, the issue here is, the liquidator also paid off 440 of debt interest, and is not sent to the StakingLPEth as profit. This means the 440 amount of underlying token (WETH) would be stuck in PoolV3, with no lpETH to redeem it.

Note that the current implementation is similar to GearboxV3. However, the profit concept is completely different, so it is incorrect for LoopFi.

CDPVault.sol
```solidity
    function liquidatePositionBadDebt(address owner, uint256 repayAmount) external whenNotPaused {
        // validate params
        if (owner == address(0) || repayAmount == 0) revert CDPVault__liquidatePosition_invalidParameters();

        // load configs
        VaultConfig memory config = vaultConfig;
        LiquidationConfig memory liqConfig_ = liquidationConfig;

        // load liquidated position
        Position memory position = positions[owner];
        DebtData memory debtData = _calcDebt(position);
        uint256 spotPrice_ = spotPrice();
        if (spotPrice_ == 0) revert CDPVault__liquidatePosition_invalidSpotPrice();
        // verify that the position is indeed unsafe
        if (_isCollateralized(calcTotalDebt(debtData), wmul(position.collateral, spotPrice_), config.liquidationRatio))
            revert CDPVault__liquidatePosition_notUnsafe();

        // load price and calculate discounted price
        uint256 discountedPrice = wmul(spotPrice_, liqConfig_.liquidationDiscount);
        // Enusure that the debt is greater than the collateral at discounted price
        if (calcTotalDebt(debtData) <= wmul(position.collateral, discountedPrice)) revert CDPVault__noBadDebt();
        // compute collateral to take, debt to repay
        uint256 takeCollateral = wdiv(repayAmount, discountedPrice);
        if (takeCollateral < position.collateral) revert CDPVault__repayAmountNotEnough();

        // account for bad debt
        takeCollateral = position.collateral;
        repayAmount = wmul(takeCollateral, discountedPrice);
        uint256 loss = calcTotalDebt(debtData) - repayAmount;

        // transfer the repay amount from the liquidator to the vault
        poolUnderlying.safeTransferFrom(msg.sender, address(pool), repayAmount);

        position.cumulativeQuotaInterest = 0;
        position.cumulativeQuotaIndexLU = debtData.cumulativeQuotaIndexNow;
        // update liquidated position
        position = _modifyPosition(
            owner,
            position,
            0,
            debtData.cumulativeIndexNow,
            -toInt256(takeCollateral),
            totalDebt
        );

@>      pool.repayCreditAccount(debtData.debt, 0, loss); // U:[CM-11]
        // transfer the collateral amount from the vault to the liquidator
        token.safeTransfer(msg.sender, takeCollateral);

        int256 quotaRevenueChange = _calcQuotaRevenueChange(-int(debtData.debt));
        if (quotaRevenueChange != 0) {
            IPoolV3(pool).updateQuotaRevenue(quotaRevenueChange); // U:[PQK-15]
        }
    }
```

PoolV3.sol
```solidity
    function repayCreditAccount(
        uint256 repaidAmount,
        uint256 profit,
        uint256 loss
    )
        external
        override
        creditManagerOnly // U:[LP-2C]
        whenNotPaused // U:[LP-2A]
        nonReentrant // U:[LP-2B]
    {
        uint128 repaidAmountU128 = repaidAmount.toUint128();

        DebtParams storage cmDebt = _creditManagerDebt[msg.sender];
        uint128 cmBorrowed = cmDebt.borrowed;
        if (cmBorrowed == 0) {
            revert CallerNotCreditManagerException(); // U:[LP-2C,14A]
        }

>       if (profit > 0) {
>           _mint(treasury, convertToShares(profit)); // U:[LP-14B]
>       } else if (loss > 0) {
            address treasury_ = treasury;
            uint256 sharesInTreasury = balanceOf(treasury_);
            uint256 sharesToBurn = convertToShares(loss);
            if (sharesToBurn > sharesInTreasury) {
                unchecked {
                    emit IncurUncoveredLoss({
                        creditManager: msg.sender,
                        loss: convertToAssets(sharesToBurn - sharesInTreasury)
                    }); // U:[LP-14D]
                }
                sharesToBurn = sharesInTreasury;
            }
            _burn(treasury_, sharesToBurn); // U:[LP-14C,14D]
        }

        _updateBaseInterest({
            expectedLiquidityDelta: -loss.toInt256(),
            availableLiquidityDelta: 0,
            checkOptimalBorrowing: false
        }); // U:[LP-14B,14C,14D]

        _totalDebt.borrowed -= repaidAmountU128; // U:[LP-14B,14C,14D]
        cmDebt.borrowed = cmBorrowed - repaidAmountU128; // U:[LP-14B,14C,14D]

        emit Repay(msg.sender, repaidAmount, profit, loss); // U:[LP-14B,14C,14D]
    }
```

## Proof of Concept

Presented above.

## Tools Used

Manual Review

## Recommended Mitigation Steps

In CDPVault: Change to `pool.repayCreditAccount(debtData.debt, debtData.accruedInterest, loss)`.

In PoolV3:

```diff
        if (profit > 0) {
            _mint(treasury, convertToShares(profit)); // U:[LP-14B]
+       }
+       if (loss > 0)
-       } else if (loss > 0) {
            ...
        }
```


## Assessed type

Other