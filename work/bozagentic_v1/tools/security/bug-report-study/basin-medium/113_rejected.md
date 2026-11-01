# #113: Frontrunning possible with boreWell creation in Aquifer.sol
Labels: ['bug', '2 (Med Risk)', 'satisfactory', 'duplicate-181']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L34-L52


# Vulnerability details

## Impact

Aquifer.sol contract is a permissionless Well registry and factory. Aquifer.sol deploys Wells by cloning a pre-deployed Well implementation. It has boreWell() which is used to clone the well implementation by using Solady LibClone.sol functions like clone() and cloneDeterministic(). The conditions for use of these functions as commented in contract.

```Solidity
     * Use `salt == 0` to deploy a new Well with `create`
     * Use `salt > 0` to deploy a new Well with `create2`
```

boreWell() in Aquifer.sol is given as,

```Solidity
File: src/Aquifer.sol

34    function boreWell(
35        address implementation,
36        bytes calldata immutableData,
37        bytes calldata initFunctionCall,
38        bytes32 salt
39    ) external nonReentrant returns (address well) {
40        if (immutableData.length > 0) {
41            if (salt != bytes32(0)) {
42                well = implementation.cloneDeterministic(immutableData, salt);
43            } else {
44                well = implementation.clone(immutableData);
45            }
46        } else {
47            if (salt != bytes32(0)) {
48                well = implementation.cloneDeterministic(salt);
49            } else {
50                well = implementation.clone();
51            }
52        }

        // Some code

```

cloneDeterministic() function under the hood uses create2. This function has used salt which means that a malicious actor can prevent a user from deploying a boreWell creation by frontrunning it with the same "salt".

Additionally, In future if this protocol is being deployed on Multichains like optimism, arbitrum, polygon additional, more-critical vulnerabilities become possible via **reorg attacks.**

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L34-L52

The "salt" is a bytes32 value that is used in boreWell creation call by the caller. This enables frontrunning to occur in the following way:

- When the boreWell creation is called by user. An attacker monitors the mempool for pending transactions that involve cloning a contract with a provided "salt".
- Upon spotting such a transaction, the attacker extracts the "salt" value.
- The attacker quickly submits their own transaction with a higher gas price, attempting to clone the contract with the same "salt" before the original transaction is mined.
- If the transaction got successful, the attacker's transaction is mined first, and the contract clone is created at the expected address.
- The original transaction will likely fail, as the contract with the expected address has already been deployed.

## Tools Used
Manual review

## Recommended Mitigation Steps
Use a salt that includes the msg.sender. That way it is not possible to front-run the transaction.

```Solidity



    function boreWell(
        address implementation,
        bytes calldata immutableData,
        bytes calldata initFunctionCall,
        bytes32 salt
    ) external nonReentrant returns (address well) {
        if (immutableData.length > 0) {
            if (salt != bytes32(0)) {
-                well = implementation.cloneDeterministic(immutableData, salt);
+                well = implementation.cloneDeterministic(keccak256(abi.encode(immutableData, salt, msg.sender)));

            } else {
                well = implementation.clone(immutableData);
            }
        } else {
            if (salt != bytes32(0)) {
-                well = implementation.cloneDeterministic(salt);
+                well = implementation.cloneDeterministic(keccak256(abi.encode(salt,msg.sender)));

            } else {
                well = implementation.clone();
            }
        }

       // Some code
```



## Assessed type

Other