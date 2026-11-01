# #253: TWAP can be easily manipulated by attacker through the sync() function, causing loss of funds
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'duplicate-136']
Accepted: False

# Lines of code

 https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L590


# Vulnerability details

## Description

Please refer to the issue titled `Implementation of Well shift() function allows attackers to completely manipulate the oracles` for relevant introduction and context.

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

There is a bug in the `sync()` function, whereby the reserves are directly updated from the contract balance, but  `updatePumps()` is not called beforehand.

```solidity
 /**
 * @dev Sync the reserves of the Well with its current balance of underlying tokens.
 */
function sync() external nonReentrant {
    IERC20[] memory _tokens = tokens();
    uint256[] memory reserves = new uint256[](_tokens.length);
    for (uint256 i; i < _tokens.length; ++i) {
        reserves[i] = _tokens[i].balanceOf(address(this));
    }
    _setReserves(_tokens, reserves);
    emit Sync(reserves);
}
```

An attacker can abuse this issue by donating ERC20 tokens to one side of the token pair in the Well, calling `sync()` to update the reserves without updating pumps, and then doing a negligible swap. At the first `swapFrom()` call, the pumps will be updated. It will appear as if the entire duration until the `sync()` call was with the wrong ratio. Both the EMA oracle and the Cumulative oracle will be skewed.

## Impact

The TWAP oracle can be arbitrarily manipulated by an attacker.


## POC

The TWAP can always be manipulated. In order for it to be profitable, the gain from the exploit of a platform dependent on the TWAP needs to be higher than the donation to the Well contract used to skew the ratio. An example is provided:

Assume a Well holding 100 ETH : 100000 USDC, Fair ratio is 1:1000. 
Last trade happens at t = T
Time is now t = T + 1000 sec.
Cumulative reserves in oracle contract are `[X, Y]`. To remind, they are calculated as 
```solidity
pumpState.cumulativeReserves[i] =    pumpState.cumulativeReserves[i].add(pumpState.lastReserves[i].mul(deltaTimestampBytes));
```

1. Attacker identifies a Lending platform which uses the TWAP to determine ETH/USD value. ETH collat ratio is 90%
2. User calls exploit contract
	- take a flashloan of 1000 ETH
	- transfer 100 ETH to the Well
	- call `sync()` , new reserves are 200 : 100,000. 
	- call `swapFrom()`,  to swap 1 wei of ETH. Pump update is triggered, with new reserve ratio:
	- Cumulative = `[X,Y] + [200 * 1000, 100000 * 1000]
	- Victim queries TWAP price, which [calculates]((https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/pumps/MultiFlowPump.sol#L307) ):
	```
	twaReserves = ([X + 200*1000, Y + 10000*1000]-[X,Y]) / 1000
	twaReserves = [200, 10000]
	```
	- Assumed ETH price is $500 USD
	- exploit contract converts 900 ETH to 900,000 USDC
	- exploit contract deposits 900,000 USDC as collateral
	- exploit contract borrows 900,000 / $500 * 90% (max loan ratio) = 1620 ETH
	- exploit contract repays 1000 ETH flashloan with loaned ETH
	- attacker exits with 620ETH of profit, minus swap fees

## Tools Used

Manual audit

## Recommended Mitigation Steps

In the `sync()` function, call the `_updatePumps()` function, even though the current reserve count is not necessary.


## Assessed type

Oracle