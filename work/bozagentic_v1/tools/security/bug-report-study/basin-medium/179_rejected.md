# #179: Absence of Error Handling when Output Amount Request is larger than Reserve
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L276
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L316


# Vulnerability details

## Impact
Absence of Error Handling and possible Reversion when Output Amount Request is larger than Reserve could complicate smart contract function

## Proof of Concept
"amountout" parameter present in function getSwapIn(...) and function swapTo(...) in src/Well.sol lack caution error in case user tries to withdraw amount higher than reserve amount. 

## Tools Used
solidity, foundry

## Recommended Mitigation Steps
revert() when amountout is higher than reserve[j]


## Assessed type

ETH-Transfer