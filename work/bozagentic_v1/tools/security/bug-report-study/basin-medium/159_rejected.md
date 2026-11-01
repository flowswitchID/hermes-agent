# #159: Aquifer#boreWell:  Malicious actor can frontrun well creation
Labels: ['bug', '2 (Med Risk)', 'satisfactory', 'duplicate-181']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L42


# Vulnerability details


## Impact

A malicious actor can used the same salt paramter to frontrun the creation of Well contract leading to DOS attacks. 

## Proof of Concept

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L42
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L48


The Aquifier.boreWell function is responsible for creating a new well. If the salt != 0, it uses the LibClone.cloneDeterministic (CREATE2) function. In this case, the address of the new well depends on the _salt parameter provided by the user. Once the user's txn is broadcasted, the _salt parameter can be viewed by anyone watching the public mempool.

An attacker can frontrun the txn with the same salt which would create the exact address created by CREATE2 call as a result this would get the victim txn to revert.


## Tools Used

Manual Review

## Recommended Mitigation Steps

It is recommended to combine salt with msg.sender

well = implementation.cloneDeterministic(immutableData, keccak256(abi.encode(msg.sender, _salt));


## Assessed type

DoS