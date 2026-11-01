# #143: No permission check for removeLiquidity and removeLiquidityOneToken functions
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/e1b03e74a87954892ff8c32dfd647972ec6e6a8f/src/Well.sol#L460
https://github.com/code-423n4/2023-07-basin/blob/e1b03e74a87954892ff8c32dfd647972ec6e6a8f/src/Well.sol#L495


# Vulnerability details

## Impact
Right now anyone can remove liquidity and we should add the permission check such as onlyOwner

## Tools Used
Manual reading

## Recommended Mitigation Steps

Add the permission check for these two functions


## Assessed type

Access Control