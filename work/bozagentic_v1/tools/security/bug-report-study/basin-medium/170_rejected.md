# #170: `removeLiquidity`   may revert  if  out tokens contains feeontransfer token 
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/84dd4472a951bfd66f4e92abd8231aa4d00f7398/src/Well.sol#L422-L434
https://github.com/code-423n4/2023-07-basin/blob/84dd4472a951bfd66f4e92abd8231aa4d00f7398/src/Well.sol#L473-L479


# Vulnerability details

## Impact
`removeLiquidity`  may revert  if  out tokens contain `feeontransfer` token 

## Proof of Concept
`_addLiquidity`  is to add liquidity to `well.` This function defines the bool parameter `feeOnTransfer` to see weather add tokens is feeontransfer tokens or not.
The issue is in the function `removeLiquidity`. There is no related `feeontransfer` token logic check, `removeLiquidity`  may revert  if  out tokens contain `feeontransfer` token 

## Tools Used
manual
## Recommended Mitigation Steps
add `feeontransfer` logic in `removeLiquidity`



## Assessed type

Error