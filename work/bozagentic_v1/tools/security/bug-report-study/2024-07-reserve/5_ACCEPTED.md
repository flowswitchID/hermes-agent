# #5: The fee in Gnosis trading isn't included in the calculation of the minBuyAmount
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_primary']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/p1/mixins/TradeLib.sol#L76-L80
https://github.com/code-423n4/2024-07-reserve/blob/3f133997e186465f4904553b0f8e86ecb7bbacbf/contracts/plugins/trading/GnosisTrade.sol#L114-L120


# Vulnerability details

## Impact
When we sell tokens to buy other tokens in a `trade`, we determine the `minimum buy amount` based on the `sell amount`. 
This means that if we receive less than this `minimum amount`, the `trade` will fail. 
Normally, we consider a worst-case scenario where we sell tokens at a `lower price` and buy tokens at a `higher price`. 
If we don’t meet the `minimum buy amount`, the `trade` should fail.

However, in `Gnosis trading`, a `fee` is applied, which means the actual `sell amount` is less than the `input amount`. 
Despite this, the `minimum buy amount` is still calculated using the `input amount`, not the actual `sell amount`. 
As a result, a `trade` that could have succeeded might fail due to this discrepancy.
## Proof of Concept
The `minimum buy amount` is calculated based on the `sell amount` as follows:
```
function prepareTradeSell(
    TradeInfo memory trade,
    uint192 minTradeVolume,
    uint192 maxTradeSlippage
) internal view returns (bool notDust, TradeRequest memory req) {
    // {buyTok} = {sellTok} * {1} * {UoA/sellTok} / {UoA/buyTok}
    uint192 b = s.mul(FIX_ONE.minus(maxTradeSlippage)).safeMulDiv(
        trade.prices.sellLow,
        trade.prices.buyHigh,
        CEIL
    );

    req.sellAmount = s.shiftl_toUint(int8(trade.sell.erc20Decimals()), FLOOR);
    req.minBuyAmount = b.shiftl_toUint(int8(trade.buy.erc20Decimals()), CEIL);
    req.sell = trade.sell;
    req.buy = trade.buy;

    return (notDust, req);
}
```
The numerical expression is as follow.
```
minBuyAmount = sellAmount * (1 - maxTradeSlippage) * sellLow / buyHigh
```
These amounts are then passed to the `Gnosis Trade` (`lines 91-92`).
```
function init(
    IBroker broker_,
    address origin_,
    IGnosis gnosis_,
    uint48 batchAuctionLength,
    TradeRequest calldata req
) external stateTransition(TradeStatus.NOT_STARTED, TradeStatus.OPEN) {
91:    require(req.sellAmount <= type(uint96).max, "sellAmount too large");
92:    require(req.minBuyAmount <= type(uint96).max, "minBuyAmount too large");

114:    uint96 _sellAmount = uint96(
115:        _divrnd(
116:            req.sellAmount * FEE_DENOMINATOR,
117:            FEE_DENOMINATOR + gnosis.feeNumerator(),
118:            FLOOR
119:        )
120:    );

  
    auctionId = gnosis.initiateAuction(
        sell,
        buy,
        endTime,
        endTime,
149:        _sellAmount,
150:        minBuyAmount,
        minBuyAmtPerOrder,
        0,
        false,
        address(0),
        new bytes(0)
    );
}
```
However, the actual `sell amount` decreases due to the `fee` in the `Gnosis Trade` (`lines 114-120`). 
This reduced `sell amount` is what gets passed to the `Gnosis contract`(`line 149~150`).

In the `Gnosis contract`, the original `sell amount` is transferred, with the excess being handled as `fees`. 
```
function initiateAuction(
    IERC20 _auctioningToken,
    IERC20 _biddingToken,
    uint256 orderCancellationEndDate,
    uint256 auctionEndDate,
    uint96 _auctionedSellAmount,  // _sellAmount
    uint96 _minBuyAmount,
    uint256 minimumBiddingAmountPerOrder,
    uint256 minFundingThreshold,
    bool isAtomicClosureAllowed,
    address accessManagerContract,
    bytes memory accessManagerContractData
) public returns (uint256) {
    _auctioningToken.safeTransferFrom(
        msg.sender,
        address(this),
        _auctionedSellAmount.mul(FEE_DENOMINATOR.add(feeNumerator)).div(
            FEE_DENOMINATOR
        ) //[0]
    );
```
As a result, when tokens are sold at a `lower price` and bought at a `higher price`—as we expected in the worst-case scenario—we may not achieve the calculated `minimum buy amount` from the actual `sell amount`. 
This could cause the `trade` to fail.
## Tools Used

## Recommended Mitigation Steps
Recalculate the `minimum buy amount` based on the actual `sell amount`.





## Assessed type

Math