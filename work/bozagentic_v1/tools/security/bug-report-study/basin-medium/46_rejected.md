# #46: Immutable values are not maintained on upgrade   
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/utils/Clone.sol#L7-L99


# Vulnerability details

## Impact
Immutable values are not maintained on upgrade   

## Proof of Concept
Immutable variables are stored in the actual contract code, in the bytecode.
If you are upgrading you cannot take the values, because they are not in the storage.
## Tools Used
mannual
## Recommended Mitigation Steps
Store the values that will be upgraded later in storage


## Assessed type

Upgradable