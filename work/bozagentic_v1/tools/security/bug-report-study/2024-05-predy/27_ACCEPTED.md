# #27: Liquidation incorrectly tries to transfer token from Market instead of liquidator if remainingMargin is negative
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'satisfactory', 'selected for report', 'sponsor confirmed', ':robot:_primary', ':robot:_14_group', 'H-04']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/main/src/libraries/logic/LiquidationLogic.sol#L106


# Vulnerability details


## Impact

Liquidation cannot be executed if there is bad debt (vault position is negative) after liquidation.

## Bug Description

See the liquidation flowchart here: https://docs.predy.finance/predy-v6/dev/architecture/flowchart#execliquidationcall

The liquidator would call a Market contract, which triggers the liquidation logic in PredyPool. Then tokens would then be swapped accordingly using the `SettlementCallbackLib`.

The issue is during the end of liquidation, if the position is entirely wiped out (e.g. `hasPosition == false` in the following code), the code checks whether there is still margin left in the vault.

1. If there is still margin left, the remaining margin would be sent to the `vault.recipient` address.
2. If there is bad debt (negative margin value), the liquidator must pay for this.

For case 2, the code tries to transfer token from `msg.sender` to PredyPool. However, the `msg.sender` is the Market protocol, and not the liquidator. This means liquidating a vault with negative margin is impossible, and this bad debt will never be cleared. What's worse, the lending fees would still accumulate for this vault, and the bad debt keeps getting larger.

```solidity
    function liquidate(
        uint256 vaultId,
        uint256 closeRatio,
        GlobalDataLibrary.GlobalData storage globalData,
        bytes memory settlementData
    ) external returns (IPredyPool.TradeResult memory tradeResult) {
        ...
        if (!hasPosition) {
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

>               // To prevent the liquidator from unfairly profiting through arbitrage trades in the AMM and passing losses onto the protocol,
>               // any losses that cannot be covered by the vault must be compensated by the liquidator
>               ERC20(pairStatus.quotePool.token).safeTransferFrom(msg.sender, address(this), uint256(-remainingMargin));
            }
        }
        ...
    }
```

## Proof of Concept

N/A

## Tools Used

Manual review

## Recommended Mitigation Steps

Transfer quoteTokens from the liquidator instead of the Market protocol.


## Assessed type

Token-Transfer