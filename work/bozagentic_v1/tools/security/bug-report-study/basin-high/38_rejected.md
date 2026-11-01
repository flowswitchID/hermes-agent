# #38: Not checking values after performing swap
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L237


# Vulnerability details

## Impact
Since the call from _swapFrom is going to an external contract, that can have modified safeTransfer and safeTransferFrom functions that can be used to drain the pool

## Proof of Concept
For instance, will look up on swapFrom function in Well.sol
``` solidity
function swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountOut) {
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn);
        amountOut = _swapFrom(fromToken, toToken, amountIn, minAmountOut, recipient);
    }

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
There is no check for the true amount of tokens that have been sent and no check for the health(balances) of the pool(pair) after the swap.

It would help to make sure that the pair contract received and "sent" the correct amount of tokens.


## Tools Used

Manual checking

## Recommended Mitigation Steps
It would be better to check all balances after performing a swap, for instance as it is done in UniswapV2
https://github.com/Uniswap/v2-core/blob/ee547b17853e71ed4e0101ccfd52e70d5acded58/contracts/UniswapV2Pair.sol#L159

The same issue:
 https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L215
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L296



## Assessed type

Token-Transfer