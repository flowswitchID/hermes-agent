# #172: Improper Validation Of create2 Return Value can cause inexisitent new well contract address to be mapped to storage in aquifier.sol
Labels: ['bug', '2 (Med Risk)', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L42
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/libraries/LibClone.sol#L122
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/libraries/LibClone.sol#L126


# Vulnerability details

## Impact
New well implementations are cloned/deployed/created using the boreWell() in aquifier.sol. When the cloneDeterministic() from LibClone.sol is used, create2 opcode is called. The function boreWell() or cloneDeterministic() from LibClone.sol does not revert properly if there is a failed contract deployment or revert from the create2 opcode as it does not properly check the returned address for bytecode. The create2 opcode will still return the expected address which will never be the zero address which is what is currently checked in cloneDeterministic() from LibClone.sol. 

It may be argued that LibClone.sol is out of scope but it is important to note that Aquifier.sol is well in scope and the chain of actions starts from Aquifier.sol. 

## Proof of Concept
Similar code4rena issue found here --> https://github.com/code-423n4/2021-10-mochi-findings/issues/155
solodit link ---> https://solodit.xyz/issues/m-13-improper-validation-of-create2-return-value-code4rena-mochi-mochi-contest-git

link to line with issue in repo --> https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/libraries/LibClone.sol#L126

in the link to line with issue in repo we can see the check is only performed to see if address is address(0) alone, but the bytecode size should be checked too to verify that there is logic at that address. 

## Tools Used
vs code, solodit.xyz
## Recommended Mitigation Steps
Update iszero(instance) to iszero(extcodesize(instance)) in the library LibClone or do the check for the new well address in the aquifer.sol before saving the new address to storage. 





## Assessed type

Library