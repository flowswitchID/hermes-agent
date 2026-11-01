# #254: Implementation of Well shift() function allows attackers to completely manipulate the oracles
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'duplicate-136']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L352


# Vulnerability details

## Description

The TWAP mechanism relies on measurements sent to the oracle at various points in time. Before reserve counts change, the TWAP is sent the last reserve counts, which are multiplied by the time passed and added to the accumulator. In MultiFlowPump, it happens here:
```solidity
for (uint256 i; i < numberOfReserves; ++i) {
    // Use a minimum of 1 for reserve. Geometric means will be set to 0 if a reserve is 0.
    pumpState.lastReserves[i] = _capReserve(
        pumpState.lastReserves[i], (reserves[i] > 0 ? reserves[i] : 1).fromUIntToLog2(), blocksPassed
    );
    pumpState.emaReserves[i] =
        pumpState.lastReserves[i].mul((ABDKMathQuad.ONE.sub(alphaN))).add(pumpState.emaReserves[i].mul(alphaN));
    pumpState.cumulativeReserves[i] =
       // @audit - TWAP update
pumpState.cumulativeReserves[i].add(pumpState.lastReserves[i].mul(deltaTimestampBytes));
}
```

`lastReserves[i]` is capped and updated with the parameter `reserves[i].price`. Then it is used to determine `cumulativeReserves[i]`. This behavior is correct, as [discussed](https://uniswapv3book.com/docs/milestone_5/price-oracle/#writing-observations) in the Uniswap v3 book. 

The safety of the TWAP relies on calling the observation function (`update()`) with the current reserve, *before* any reserve changes take place. Updating happens in the `_updatePumps` call:
```solidity
reserves = _getReserves(_numberOfTokens);
if (numberOfPumps() == 0) {
    return reserves;
}
// gas optimization: avoid looping if there is only one pump
if (numberOfPumps() == 1) {
    Call memory _pump = firstPump();
    // Don't revert if the update call fails.
    try IPump(_pump.target).update(reserves, _pump.data) {}
    catch {
        // ignore reversion. If an external shutoff mechanism is added to a Pump, it could be called here.
    }
```

It is called in the following functions which change reserve counts:

1. `_swapFrom()`
2. `swapTo()`
3. `_addLiquidity()`
4. `removeLiquidity()`
5. `removeLiquidityOneToken()`
6. `removeLiquidityImbalanced()`

However, it is not called in the `shift()` function, which is very similar to `swapFrom()` and updates reserves counts.

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
	 ...
	 
function shift(
    IERC20 tokenOut,
    uint256 minAmountOut,
    address recipient
) external nonReentrant returns (uint256 amountOut) {
    IERC20[] memory _tokens = tokens();
    uint256[] memory reserves = new uint256[](_tokens.length);	 
	...
```

At the end of the function, it will update the reserves from the current balances:
```solidity
if (amountOut >= minAmountOut) {
    tokenOut.safeTransfer(recipient, amountOut);
    reserves[j] -= amountOut;
    _setReserves(_tokens, reserves);
    emit Shift(reserves, tokenOut, amountOut, recipient);
} else {
    revert SlippageOut(amountOut, minAmountOut);
}
```

This means an attacker can easily manipulate the TWAP price. They will transfer tokens to the contract and use  `shift()` to change the reserve count to an extreme ratio, then swap back the tokens using a normal `swapFrom()` call, which will set update the oracle with the *post-shift* reserve counts. It will appear as if the entire duration until the shift was with the extreme ratio. Both the EMA oracle and the Cumulative oracle will be skewed.

## Impact

The TWAP oracle can be arbitrarily manipulated by an attacker.


## POC

Assume a Well holding 100 ETH : 100000 USDC, Fair ratio is 1:1000. 
Last trade happens at t = T
Time is now t = T + 1000 sec.
Cumulative reserves in oracle contract are `[X, Y]`. To remind, they are calculated as 
```solidity
pumpState.cumulativeReserves[i] =    pumpState.cumulativeReserves[i].add(pumpState.lastReserves[i].mul(deltaTimestampBytes));
```
1. User calls exploit contract
	- take a flashloan of 10,000 ETH
	- transfer all ETH to the Well
	- call `shift()` , new reserves are 10100 : 990. Receive `100000-990` USDC to wallet
	- call `swapFrom()`,  passing received USDC from `shift()`. Pool returns to 100 : 100,000, user receives 10,000 ETH back
	- user repays flashloan
2. During `swapFrom()`, cumulative reserves were updated:
	- Cumulative = `[X,Y] + [10100 * 1000, 990 * 1000]
3. The TWAP oracle has been poisoned. 

For example, a victim now queries the TWAP price in the last 1000 sec, [using](https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/pumps/MultiFlowPump.sol#L307) 
`readTwaReserves(Well, [x,y], T)`:
It will calculate:
```
twaReserves = ([X + 10100*1000, Y + 990*1000]-[X,Y]) / 1000
twaReserves = [10100, 990]
```

Calculation shows the TWAP price for the past 1000 seconds is 1 ETH = 0.098 USDC. 
Attacker can now exploit any user of the TWAP through uncollateralized loans, swaps at wrong ratio, or any other target-specific way.

## Tools Used

Manual audit

## Recommended Mitigation Steps

In the `shift()` function, call the `_updatePumps()` function, even though the current reserve count is not necessary.




## Assessed type

Oracle