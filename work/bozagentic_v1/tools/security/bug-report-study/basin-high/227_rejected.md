# #227: You can expand your version of well in Aquifer.boreWell() with unpredictable results
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Aquifer.sol#L34-L39


# Vulnerability details

## Impact
boreWell() takes an implementation parameter. This parameter is not checked in any way. Thus, the user can pass any of his parameters and expand his well option.

This can lead to unpredictable consequences.

## Proof of Concept
1. The user creates his own instance similar to well
2. The user calls the function boreWell() with the address of the implementation of his version of well

## Tools Used
Manual review

## Recommended Mitigation Steps
Add address verification Well available for cloning


## Assessed type

Context