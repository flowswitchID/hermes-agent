# #105: For FeeOnTransfer tokens, it is more profitable to call swapFrom / addLiquidity, so no one will call swapFromFeeOnTransfer / addLiquidityFeeOnTransfer
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L186-L213


# Vulnerability details

## Impact

The Well provides two entries for swapFrom: `swapFrom` is calculated based on the number of tokens before transfer, and `swapFromFeeOnTransfer` is calculated based on the number of tokens actually transferred.
Therefore, for feeOnTransfer tokens, `swapFrom` is more profitable, and no one will call `swapFromFeeOnTransfer`. The Same for addLiquidity.

## Proof of Concept

```solidity
function _swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient
    ) internal returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);
        (uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken);

        reserves[i] += amountIn;
        uint256 reserveJBefore = reserves[j];
        reserves[j] = _calcReserve(wellFunction(), reserves, j, totalSupply());

        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.
        amountOut = reserveJBefore - reserves[j];
        if (amountOut < minAmountOut) {
            revert SlippageOut(amountOut, minAmountOut);
        }

        toToken.safeTransfer(recipient, amountOut);
        emit Swap(fromToken, toToken, amountIn, amountOut, recipient);
        _setReserves(_tokens, reserves);
    }
```

Both entry functions call the `_swapFrom` function, which computes `amountOut` from the `amountIn` argument.
Therefore, the larger `amountIn` is, the higher the revenue will be. Users will call `swapFrom` to obtain more revenue, while well will overestimate `reserves[i]` and eventually run out of funds.

## Tools Used

Manual review

## Recommended Mitigation Steps

Do not need to provide two entrances, `_safeTransferFromFeeOnTransfer` should always be used to calculate amountIn. 





## Assessed type

Uniswap