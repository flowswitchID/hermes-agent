# #10: Liquidation process may be reverted because of slipage control
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_primary', ':robot:_19_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/libraries/SlippageLib.sol#L21-L44


# Vulnerability details

## Impact
Liquidation process may be reverted when the difference between TWAP price and actual price is larger than slippage control.

## Proof of Concept
When one position is not safe, the liquidator will liquidate this position. When we liquidate one position, we will check the difference between the actual price and twap price. If the difference is larger than the `slippageTolerance`, the liquidation will be reverted because the system thinks the liquidator takes too much profit.

The vulnerability is that in some extreme market condition, some base tokens(eg, ARB) may increase or drop rapidly. This will cause the difference between the actual price and the TWAP(30minites) price is large. If some positions are unsafe, liquidation process may be reverted because of the slippage control.

The slippage control aims to prevent the liquidator to gain too much profits via arbitrage. However, this slippage control might block some normal case.

 
```javascript
    function liquidate(
        uint256 vaultId,
        uint256 closeRatio,
        GlobalDataLibrary.GlobalData storage globalData,
        bytes memory settlementData
    ) external returns (IPredyPool.TradeResult memory tradeResult) {
        ......
        // Check if the price is within the slippage tolerance range to ensure that the price does not become
        // excessively favorable to the liquidator.
        // sqrtOraclePrice --> twap price
        SlippageLib.checkPrice(
            sqrtOraclePrice,
            tradeResult,
            slippageTolerance,
            tradeParams.tradeAmountSqrt == 0 ? 0 : _MAX_ACCEPTABLE_SQRT_PRICE_RANGE
        );

```
### Poc
This will be reverted because of `Reason: SlippageTooLarge()`
```javascript
    function testLiquidateSucceedsWithInsolvent() public {
        IPredyPool.TradeParams memory tradeParams =
            IPredyPool.TradeParams(1, 0, -48 * 1e7, 0, abi.encode(_getTradeAfterParams(1e8)));

        _tradeMarket.trade(tradeParams, _getSettlementData(Constants.Q96));

        _movePrice(true, 8 * 1e16);

        vm.warp(block.timestamp + 1 minutes);

        _movePrice(true, 2 * 1e16);

        vm.warp(block.timestamp + 29 minutes);
        _tradeMarket.execLiquidationCall(1, 1e18, _getSettlementData(Constants.Q96 * 13000 / 10000));
        //checkMarginEqZero(1);
    }
```
## Tools Used
Manual

## Recommended Mitigation Steps
Bring chainlink oracle to calculate the slippage control.





## Assessed type

DoS