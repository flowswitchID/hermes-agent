# #19: Gamma trading may be blocked when there is not enough liquidity
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_primary', ':robot:_28_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/libraries/Perp.sol#L426-L453


# Vulnerability details

## Impact
Traders' gamma position may not be closed because there is not enough liquidity to burn. Traders may face more risk because they cannot close their liquidity as they expect.

## Proof of Concept
When traders open one gamma position with one positive `_tradeSqrtAmount`, predy protocol will mint some uniswap v3 liquidity according to the related pair's configuration. If traders open one gamma position with one negative `_tradeSqrtAmount`, predy protocol will burn some uniswap v3 pool liquidities.

The vulnerability is that one trader can burn other traders' minted liquidity when the trader open one gamma position with one negative `_tradeSqrtAmount`.

For example:
1. Alice opens one gamma position with +100 `_tradeSqrtAmount`, Assume we will mint 100 uniswap v3 liquidity.
2. Bob opens one gamma position with -50 `_tradeSqrtAmount`, predy pool will burn 50 liquidity.
3. If Alice wants to close her position, predy pool expects to burn 100 uniswap v3 liquidities and will be reverted because there is not enough liquidity left in predy pool.

```javascript
    function computeRequiredAmounts(
        SqrtPerpAssetStatus storage _sqrtAssetStatus,
        bool _isQuoteZero,
        UserStatus memory _userStatus,
        int256 _tradeSqrtAmount
    ) internal returns (int256 requiredAmountUnderlying, int256 requiredAmountStable) {
        ......
        int256 requiredAmount0;
        int256 requiredAmount1;
        if (_tradeSqrtAmount > 0) {
            (requiredAmount0, requiredAmount1) = increase(_sqrtAssetStatus, uint256(_tradeSqrtAmount));
            if (_sqrtAssetStatus.totalAmount == _sqrtAssetStatus.borrowedAmount) {
                // if available liquidity was 0 and added first liquidity then update last fee growth
                saveLastFeeGrowth(_sqrtAssetStatus);
            }
        } else if (_tradeSqrtAmount < 0) {
            (requiredAmount0, requiredAmount1) = decrease(_sqrtAssetStatus, uint256(-_tradeSqrtAmount));
        }
```

### Poc
Add this test in ExecuteOrder.t.sol, and this test case will be reverted because there is not enough liquidity.
```javascript
    function testExecuteOrderSucceedsForOpen() public {
        GammaOrder memory order =
            _createOrder(from1, 0, block.timestamp + 100, 1, 0, 0, 1000, 2 * 1e6, Constants.Q96);
        //IPredyPool.TradeResult memory tradeResult = gammaTradeMarket.executeTrade(order, _sign(order, fromPrivateKey1), _getSettlementDataV3(Constants.Q96));
        IPredyPool.TradeResult memory tradeResult = gammaTradeMarket.executeTrade(order, _sign(order, fromPrivateKey1), _getSettlementDataV3(Constants.Q96));

        order = _createOrder(from2, 1, block.timestamp + 100, 1, 0, 0, -500, 2 * 1e6, Constants.Q96);
        tradeResult = gammaTradeMarket.executeTrade(order, _sign(order, fromPrivateKey2), _getSettlementDataV3(Constants.Q96));

        order = _createOrder(from1, 1, block.timestamp + 100, 1, 1, 0, -1000, 0, Constants.Q96);
        tradeResult = gammaTradeMarket.executeTrade(order, _sign(order, fromPrivateKey1), _getUniSettlementDataV3(Constants.Q96));
        //tradeResult = gammaTradeMarket.executeTrade(order, _sign(order, fromPrivateKey1), _getSettlementDataV3(Constants.Q96));
    }
```
## Tools Used
Manual

## Recommended Mitigation Steps
Honestly, there is not one easy fixed solution. Need to revisit the scenario.


## Assessed type

DoS