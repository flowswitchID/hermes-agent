# #293: _addLiquidity() function will revert in first call
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'sponsor disputed', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L413-L444
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ProportionalLPToken2.sol#L15-L24


# Vulnerability details

## Impact
The first user cant calls the _addLiquidity() function because this function doesn't handle the first call.

_addLiquidity() function is calculate lp amount by calling calcLPTokenUnderlying() function. so this function has a division for lpTokenSupply. in this scenario lpTokenSupply is zero when no one added liquidity but the issue is when the user wants to add liquidity, the function will revert cause of division by zero, So no one be able to add liquidity.

## Proof of Concept
Alice wants to add liquidity for the first time.
lpTokenSupply is zero so when she calls the _addLiquidity() function, it will revert the cause of division by zero.

## Tools Used
Manual Review

## Recommended Mitigation Steps
Consider a specific amount of lp tokens for a first call, or any implementation that handles this issue.


## Assessed type

Under/Overflow