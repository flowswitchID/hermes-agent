# #278: Users can swap tokens through `shift()` function without `_updatePumps()` 
Labels: ['bug', '3 (High Risk)', 'partial-50', 'edited-by-warden', 'duplicate-136']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L352-L377


# Vulnerability details

## Impact
Any user can swap tokens just transferring tokens to the contract in a batch with calling [`shift`](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L352-L377) function. The problem is that the `shift` doesn't call the `_updatePumps` function which `update` oracle. This way attackers can exploit this vulnerability to manipulate the price oracle. 

## Proof of Concept
The `shift` function does not contain `_updatePumps` call, which returns a saved list of `reserves`, because it uses another flow with receiving `reserves` directly from current `token.balanceOf(address(this))`.
```solidity
358:        uint256[] memory reserves = new uint256[](_tokens.length);
359:
360:        // Use the balances of the pool instead of the stored reserves.
361:        // If there is a change in token balances relative to the currently
362:        // stored reserves, the extra tokens can be shifted into `tokenOut`.
363:        for (uint256 i; i < _tokens.length; ++i) {
364:            reserves[i] = _tokens[i].balanceOf(address(this));
365:        }
```
Other important functions in the `Well` contract receive `reserves` from `_updatePumps`. This way these functions [`update`](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L645-L670) oracle prices but `shift` doesn't.
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L223
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L273
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L420
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L467
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L503
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L555

At the same time,the `shift` function can be used for swap tokens in a batch with tokens transfering into the `Well` contract.

## Tools Used
Manual review

## Recommended Mitigation Steps
I suggest calling the `_updatePumps` in the `shift`.






## Assessed type

Oracle