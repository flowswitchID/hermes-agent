# #187: `Aquifer.boreWell` can be front-runned with malicious `initFunctionCall` 
Labels: ['bug', '2 (Med Risk)', 'downgraded by judge', 'satisfactory', 'duplicate-181']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Aquifer.sol#L34


# Vulnerability details

## Impact

A benign user can call `Aquifer.boreWell` with `salt` to deploy a new Well with `create2`. However the implementation of `Aquifer.boreWell` is vulnerable to front-running attacks. A malicious user can front-run the transaction with malicious `initFunctionCall`.

## Proof of Concept

`Aquifer.boreWell` uses `create2` to deploy a new Well if `salt > 0`. And then it performs `well.call(initFunctionCall)` if `initFunctionCall.length > 0`.
https://github.com/code-423n4/2023-07-basin/blob/main/src/Aquifer.sol#L34
```solidity
    function boreWell(
        address implementation,
        bytes calldata immutableData,
        bytes calldata initFunctionCall,
        bytes32 salt
    ) external nonReentrant returns (address well) {
        if (immutableData.length > 0) {
            if (salt != bytes32(0)) {
                well = implementation.cloneDeterministic(immutableData, salt);
            } else {
                well = implementation.clone(immutableData);
            }
        } else {
            if (salt != bytes32(0)) {
                well = implementation.cloneDeterministic(salt);
            } else {
                well = implementation.clone();
            }
        }

        if (initFunctionCall.length > 0) {
            (bool success, bytes memory returnData) = well.call(initFunctionCall);
            if (!success) {
                // Next 5 lines are based on https://ethereum.stackexchange.com/a/83577
                if (returnData.length < 68) revert InitFailed("");
                assembly {
                    returnData := add(returnData, 0x04)
                }
                revert InitFailed(abi.decode(returnData, (string)));
            }
        }

        …
    }
```

Since the `salt` is unrelated to the `initFunctionCall`. A malicious user can front-run the transaction with malicious `initFunctionCall`. Since the well implementation is user-defined, the impact of this attack could be significant.

## Tools Used

Manual Review

## Recommended Mitigation Steps

There are two methods to mitigate this issue:
Add `msg.sender` to the `salt`
```diff
    function boreWell(
        address implementation,
        bytes calldata immutableData,
        bytes calldata initFunctionCall,
        bytes32 salt
    ) external nonReentrant returns (address well) {
        if (immutableData.length > 0) {
            if (salt != bytes32(0)) {
-               well = implementation.cloneDeterministic(immutableData, salt);
+               well = implementation.cloneDeterministic(immutableData, keccak256(abi.encodePacked(salt, msg.sender)));
            } else {
                well = implementation.clone(immutableData);
            }
```
Or add `initFunctionCall` to the `salt`
```diff
    function boreWell(
        address implementation,
        bytes calldata immutableData,
        bytes calldata initFunctionCall,
        bytes32 salt
    ) external nonReentrant returns (address well) {
        if (immutableData.length > 0) {
            if (salt != bytes32(0)) {
-               well = implementation.cloneDeterministic(immutableData, salt);
+               well = implementation.cloneDeterministic(immutableData, keccak256(abi.encodePacked(salt, initFunctionCall)));
            } else {
                well = implementation.clone(immutableData);
            }
```



## Assessed type

Other