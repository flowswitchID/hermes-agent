# #9: Liquidators may get more profits than expected
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', 'edited-by-warden', ':robot:_65_group', 'duplicate-189']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/libraries/logic/LiquidationLogic.sol#L39-L109


# Vulnerability details

## Impact
Liquidators may gain more profits and pass loss to the protocol.

## Proof of Concept
When one position is not safe, liquidators can liquidate this position. If this position's left margin is negative, the liquidator needs to cover these negative margin. This aims to avoid the liquidator gain unfairly profit and pass loss to the protocol.
But the vulnerability is that this mechanism only works when the liquidator liquidates the whole position. It means if the liquidator liquidates 99% of the unsafe position, the liquidator can bypass the above mechanism's check and gain more profit.
```javascript
    function liquidate(
        uint256 vaultId,
        uint256 closeRatio,
        GlobalDataLibrary.GlobalData storage globalData,
        bytes memory settlementData
    ) external returns (IPredyPool.TradeResult memory tradeResult) {
        require(closeRatio > 0 && closeRatio <= 1e18, "ICR");
        ......
        uint256 sentMarginAmount = 0;
        // hasPosition means the position is empty.
        if (!hasPosition) {
            int256 remainingMargin = vault.margin;
            if (remainingMargin > 0) {
                ......
            } else if (remainingMargin < 0) {
                vault.margin = 0;

                // To prevent the liquidator from unfairly profiting through arbitrage trades in the AMM and passing losses onto the protocol,
                // any losses that cannot be covered by the vault must be compensated by the liquidator
                ERC20(pairStatus.quotePool.token).safeTransferFrom(msg.sender, address(this), uint256(-remainingMargin));
            }
        }
```
### Poc
In below case, when we liquidate 100% position, this liquidation process will be reverted. But when we liquidate 99% position, the liquidation process can work.
```javascript
    function testLiquidateSucceedsWithInsolvent() public {
        IPredyPool.TradeParams memory tradeParams =
            IPredyPool.TradeParams(1, 0, -48 * 1e7, 0, abi.encode(_getTradeAfterParams(1e8)));

        _tradeMarket.trade(tradeParams, _getSettlementData(Constants.Q96));

        _movePrice(true, 8 * 1e16);

        vm.warp(block.timestamp + 1 minutes);

        _movePrice(true, 2 * 1e16);

        vm.warp(block.timestamp + 29 minutes);
        console.log("Trigger liquidate");
        _tradeMarket.execLiquidationCall(1, 0.99e18, _getSettlementData(Constants.Q96 * 12500 / 10000));
        //checkMarginEqZero(1);
    }
```
## Tools Used
Manual

## Recommended Mitigation Steps
Even if this position is not completed closed, we need to check whether the left margin is negative to prevent the liquidators gain too much unexpected profits.







## Assessed type

Context