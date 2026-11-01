# #57: Users can bypass reserve update to MultiFlowPump by directly trading through shift()
Labels: ['bug', '3 (High Risk)', 'partial-50', 'edited-by-warden', 'duplicate-136']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L352-L358
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L645


# Vulnerability details

## Impact
In Well.sol, all token trading and liquidity changing operations are invoked with `_updatePumps()` hook to pass reserve change to the Pump, except for reserve changes by calling `shift()`. 

As a result, any reserve modification from `shift()` will not be updated in any pumps which easily creates a deep discrepancy between the well and the pump. 

Because under normal conditions, any reserve changes from `shift()` will not be picked up by any pumps and this can also be easily exploited, I evaluate this to be High in severity.

## Proof of Concept
The intended behavior is to update the pumps with any operation that modifies the Well’s reserves. This implemented in `_swapFrom()`,`swapTo()`,`_addLiquidity()`, `removeLiquidity` etc. In these functions, `_updatePumps()` hook will be called, which pass current token reserves to the pumps through 'update()`. 

```solidity
//Well.sol
    function _swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient
    ) internal returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
|>        uint256[] memory reserves = _updatePumps(_tokens.length);
...
```
```solidity
//Well.sol
    function _updatePumps(
        uint256 _numberOfTokens
    ) internal returns (uint256[] memory reserves) {
...
|>          try IPump(_pump.target).update(reserves, _pump.data) {} catch {}
...
```
However, `shift()` which also allows users to trade and modify token reserves doesn't implement `_updatePumps()` or other mechanisms to update reserves to the pumps. This creates an easy bypass for token reserve changes not picked up by any pumps, which can be exploited by malicious uers.
```solidity
//Well.sol
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);
        // Use the balances of the pool instead of the stored reserves.
        // If there is a change in token balances relative to the currently
        // stored reserves, the extra tokens can be shifted into `tokenOut`.
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(address(this));
        }
        uint256 j = _getJ(_tokens, tokenOut);
        amountOut =
            reserves[j] -
            _calcReserve(wellFunction(), reserves, j, totalSupply());
        if (amountOut >= minAmountOut) {
            tokenOut.safeTransfer(recipient, amountOut);
            reserves[j] -= amountOut;
            _setReserves(_tokens, reserves);
            emit Shift(reserves, tokenOut, amountOut, recipient);
        } else {
            revert SlippageOut(amountOut, minAmountOut);
        }
    }
```

## Tools Used
Manual
Vscode
## Recommended Mitigation Steps
use `_updatePumps()`  for `shift()` as well since it also modifies the reserve.





## Assessed type

Other