# #221: Pool address predictability creates many problems
Labels: ['bug', '2 (Med Risk)', 'downgraded by judge', 'satisfactory', 'duplicate-181']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Aquifer.sol#L34-L52


# Vulnerability details

## Impact
The Aquifer.boreWell function is responsible for creating new Well. This is done using the LibClone.cloneDeterministic function.

The address of the new Well depends solely on the _salt and/or immutableData parameter provided by the user. Once a user create transaction is broadcast, the _salt and/or immutableData parameter can be viewed by anyone viewing the public mempool.

This may result in a DoS for Aquifer.boreWell.

## Proof of Concept
If the user intends to create a Well, his create txn can be forcibly revoked by an attacker by deploying the pool to himself using the user's salt. Here's how it might happen:

The user broadcasts the pool creation txn with salt XXX and/or immutableData.
The attacker preempts the user's txn and creates a pool for themselves using the same XXX salt and/or immutableData.
The initial user creation txn is returned because the attacker pool already exists at the predefined address.
This attack can be repeated over and over, resulting in a DoS for the Aquifer.boreWell function.

A similar issue is described in https://github.com/code-423n4/2023-04-caviar-findings/issues/419.

## Tools Used
Manual review

## Recommended Mitigation Steps
Consider making the upcoming pool address a specific user by concatenating the salt value with the user's address.
bytes32 salt = keccak256(abi.encode(msg.sender, _salt))


## Assessed type

Context