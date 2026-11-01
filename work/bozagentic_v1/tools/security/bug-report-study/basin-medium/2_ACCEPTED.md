# #2: _getArgBytes in ClonePlus.sol (used by Well.sol) overflows & corrupts memory
Labels: ['bug', '2 (Med Risk)', 'disagree with severity', 'downgraded by judge', 'primary issue', 'sponsor confirmed', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/7e51c025d32aff3f2456842c83cda66cda274d11/src/utils/ClonePlus.sol#L37 https://github.com/code-423n4/2023-07-basin/blob/7e51c025d32aff3f2456842c83cda66cda274d11/src/Well.sol#L91 https://github.com/code-423n4/2023-07-basin/blob/7e51c025d32aff3f2456842c83cda66cda274d11/src/Well.sol#L106 https://github.com/code-423n4/2023-07-basin/blob/7e51c025d32aff3f2456842c83cda66cda274d11/src/Well.sol#L177


# Vulnerability details

`_getArgBytes` in ClonePlus.sol initializes `bytesLen` bytes in memory; then, possibly due to an incorrect copy/paste from `getArgIERC20Array`, it populates them by copying over `32 * bytesLen` bytes (because of the 5-bits shift), therefore overflowing in the operation and corrupting the memory adjacent to the destination.

## Impact
Since in Solidity [memory is not cleared within internal calls](https://docs.soliditylang.org/en/v0.8.20/control-structures.html#function-calls), code executed after the faulty inline assembly may have unpredictable behavior. Without a target bytecode, it's difficult to assess precisely what the impact can be or provide a PoC, but at the same time, it's also hard to assess what the impact *cannot* be. I would call this a low-probability-but-high-risk finding.

Examples of code that can misbehave are the pieces of logic following `_getArgBytes` calls, i.e.:
 - `pumps()`, in `updatePumps()`, called when `reserves` are already in memory and yet to be used for swap/liquidity operations
 - `wellFunction()`, also called by token-moving logic with critical data like `reserves` already in memory and not yet used 

## Proof of Concept
I hope you excuse me if I don't go down the rabbit hole here. A strong indication is however that by applying the below mitigation, no tests are broken.

## Tools Used
Visual inspection

## Recommended Mitigation Steps
Remove the 5-bits shift operation in the `_getArgBytes` inline assembly to copy only the intended `bytesLen` bytes:
```
            calldatacopy(add(data, ONE_WORD), offset, bytesLen)
```


## Assessed type

Library