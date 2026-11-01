# #44: Users can call autoClose/autoHedge for other user position in GammaTradeMarket
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_206_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/main/src/markets/gamma/GammaTradeMarket.sol#L227
https://github.com/code-423n4/2024-05-predy/blob/main/src/markets/gamma/GammaTradeMarket.sol#L274


# Vulnerability details


## Impact

Users can call autoClose/autoHedge for other user position in GammaTradeMarket, and manipulate other users vault position.

## Bug Description

Here we take autoClose function as an example. It does not check for any signed messages with permit2, this means users can freely call this with positionId set to another user's vaultId to manipulate other user vaults.

They can manipulate settlementParams (used in swap) and mess with the vault value, such as reducing its position value (e.g. buying baseToken at a very high price).

```solidity
    function autoClose(uint256 positionId, SettlementParamsV3 memory settlementParams)
        external
        returns (IPredyPool.TradeResult memory tradeResult)
    {
        // save user position
        GammaTradeMarketLib.UserPosition memory userPosition = userPositions[positionId];

        if (userPosition.vaultId == 0 || positionId != userPosition.vaultId) {
            revert PositionNotFound();
        }

        // check auto close condition
        uint256 sqrtPrice = _predyPool.getSqrtIndexPrice(userPosition.pairId);

        (bool closeRequired, uint256 slippageTorelance, GammaTradeMarketLib.CallbackType triggerType) =
            GammaTradeMarketLib.validateCloseCondition(userPosition, sqrtPrice);

        if (!closeRequired) {
            revert AutoCloseTriggerNotMatched();
        }

        // execute close
        DataType.Vault memory vault = _predyPool.getVault(userPosition.vaultId);

        IPredyPool.TradeParams memory tradeParams = IPredyPool.TradeParams(
            userPosition.pairId,
            userPosition.vaultId,
            -vault.openPosition.perp.amount,
            -vault.openPosition.sqrtPerp.amount,
            abi.encode(CallbackData(triggerType, userPosition.owner, 0))
        );

        if (tradeParams.tradeAmount == 0 && tradeParams.tradeAmountSqrt == 0) {
            revert AlreadyClosed();
        }

        tradeResult = _predyPool.trade(tradeParams, _getSettlementDataFromV3(settlementParams, msg.sender));

        SlippageLib.checkPrice(sqrtPrice, tradeResult, slippageTorelance, SlippageLib.MAX_ACCEPTABLE_SQRT_PRICE_RANGE);
    }
```

## Proof of Concept

N/A

## Tools Used

Manual review

## Recommended Mitigation Steps

Add a signature check in autoClose/autoHedge.


## Assessed type

Access Control