# #2: `CDPVault.sol#liquidatePositionBadDebt()` does correctly handle profit and loss
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', ':robot:_primary', ':robot:_27_group', 'H-02']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-10-loopfi/blob/main/src/CDPVault.sol#L702
https://github.com/code-423n4/2024-10-loopfi/blob/main/src/PoolV3.sol#L593


# Vulnerability details


## Impact

When liquidating bad debt, the profit and loss is not correctly handled. This will cause incorrect accounting to lpETH stakers.

## Bug Description

*Note: This is based on the 2024-07 Loopfi contest https://github.com/code-423n4/2024-07-loopfi-findings/issues/57 issue. This protocol team applied a fix, but the fix is incomplete.*

There are two issues that needs to be fixed in the new codebase:

1. The `profit` that is passed in `pool.repayCreditAccount(debtData.debt, profit, loss);` should actually use `debtData.accruedInterest`. This is because we should first "assume" full debt and interest is paid off, and calculate the loss part independently.

2. The `loss` is correctly calculated in PoolV3#repayCreditAccount, the if-else branch is incorrectly implemented. Currently it can't handle the case where both profit and loss is non-zero. This would cause a issue that the loss will not be accounted, and will ultimately cause loss to lpETH holders (loss will be implicitly added to the users who hold lpETH) instead of lpETH stakers.

Note that the second fix was also suggested in the original issue, but it isn't applied.

CDPVault.sol
```solidity
        takeCollateral = position.collateral;
        repayAmount = wmul(takeCollateral, discountedPrice);
        uint256 loss = calcTotalDebt(debtData) - repayAmount;
        uint256 profit;
        if (repayAmount > debtData.debt) {
@>          profit = repayAmount - debtData.debt;
        }
        ...
@>      pool.repayCreditAccount(debtData.debt, profit, loss); // U:[CM-11]
        // transfer the collateral amount from the vault to the liquidator
        token.safeTransfer(msg.sender, takeCollateral);
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
        ...
        if (profit > 0) {
            _mint(treasury, _convertToShares(profit)); // U:[LP-14B]
@>      } else if (loss > 0) {
            address treasury_ = treasury;
            uint256 sharesInTreasury = balanceOf(treasury_);
            uint256 sharesToBurn = _convertToShares(loss);
            if (sharesToBurn > sharesInTreasury) {
                unchecked {
                    emit IncurUncoveredLoss({
                        creditManager: msg.sender,
                        loss: _convertToAssets(sharesToBurn - sharesInTreasury)
                    }); // U:[LP-14D]
                }
                sharesToBurn = sharesInTreasury;
            }
            _burn(treasury_, sharesToBurn); // U:[LP-14C,14D]
        }
        ...
    }
```

## Proof of Concept

N/A

## Tools Used

Manual Review

## Recommended Mitigation Steps

In CDPVault: Change to `pool.repayCreditAccount(debtData.debt, debtData.accruedInterest, loss)`.

In PoolV3:

```solidity
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