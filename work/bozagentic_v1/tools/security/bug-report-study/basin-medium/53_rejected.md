# #53: A malicious user in `Well.sol` can use addLiquidity with fee on transfer
Labels: ['bug', '2 (Med Risk)', 'unsatisfactory', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L392


# Vulnerability details

## Impact
Loss of funds, the reserves is not going to be correct

## Proof of Concept 

A malicious user can use `addLiquidity()`, however that there is `addLiquidityFeeOnTransfer`

## Tools Used
manul
## Recommended Mitigation Steps
check if the tokens has fee-on-transfer


## Assessed type

Token-Transfer