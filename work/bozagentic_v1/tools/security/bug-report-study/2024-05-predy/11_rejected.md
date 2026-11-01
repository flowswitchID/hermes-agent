# #11: Gamma trading may be blocked because liquidity is reallocated.
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_28_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/libraries/Perp.sol#L202-L252


# Vulnerability details

## Impact
Function `reallocate` may burn current position's liquidity and mint liquidity in one new position. Gamma trading may be reverted because there is not enough liquidity to burn.

## Proof of Concept
When one pair meets the allocation condition, the pair's liquidities in Uniswap v3 pool will be burned and minted in one new position based on current tick and range.

The vulnerability exists in function `getAvailableLiquidityAmount`. When we calculate the liquidities, we get liquidities via position key `_controllerAddress, _tickLower, _tickUpper`. The issue is that it's quite probable that several pairs have the same `_tickLower` and `_tickUpper`. 

For example: 
PairA and PairB share the same `_tickLower` and `_tickUpper`. When PairA match the allocation condition, all liquidities belong to both PairA and PairB will be allocated to the new position. 
Now if one trader wants to trade in PairB and need to burns some liquidities, the operation will be reverted because there is zero balance in current position.

```javascript
    function reallocate(
        DataType.PairStatus storage _assetStatusUnderlying,
        SqrtPerpAssetStatus storage _sqrtAssetStatus
    ) internal returns (bool, bool, int256 deltaPositionBase, int256 deltaPositionQuote) {
        // get related uniswap v3 pool' currentTick
        (uint160 currentSqrtPrice, int24 currentTick,,,,,) = IUniswapV3Pool(_sqrtAssetStatus.uniswapPool).slot0();
        ......
        uint128 totalLiquidityAmount = getAvailableLiquidityAmount(
            address(this), _sqrtAssetStatus.uniswapPool, _sqrtAssetStatus.tickLower, _sqrtAssetStatus.tickUpper
        );
        ......
        rebalanceForInRange(_assetStatusUnderlying, _sqrtAssetStatus, currentTick, totalLiquidityAmount);
}

```
```javascript
    function getAvailableLiquidityAmount(
        address _controllerAddress,
        address _uniswapPool,
        int24 _tickLower,
        int24 _tickUpper
    ) internal view returns (uint128) {
        bytes32 positionKey = PositionKey.compute(_controllerAddress, _tickLower, _tickUpper);

        (uint128 liquidity,,,,) = IUniswapV3Pool(_uniswapPool).positions(positionKey);

        return liquidity;
    }
```

## Tools Used
Manual

## Recommended Mitigation Steps
When we allocate one pair, we should burn/mint the liquidities belong to this pair.





## Assessed type

DoS