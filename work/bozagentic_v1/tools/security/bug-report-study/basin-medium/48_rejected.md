# #48: USDC and USDT have 6 decimals, but on other chains have 18 decimals
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibContractInfo.sol#L52-L56


# Vulnerability details

## Impact
Loss of funds of user, wrong calculations, revert

## Proof of Concept
On BNB chain USDC and USDT have 18 decimals, this way the program will revert
## Tools Used
manual 
## Recommended Mitigation Steps
use ERC20.decimals() function 


## Assessed type

Decimal