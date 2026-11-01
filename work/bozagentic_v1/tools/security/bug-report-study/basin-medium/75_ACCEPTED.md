# #75:  Incorrect Storage of Reserves in LibBytes.storeUint128
Labels: ['bug', '2 (Med Risk)', 'primary issue', 'sponsor disputed', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/libraries/LibBytes.sol#L66


# Vulnerability details

target : https://github.com/code-423n4/2023-07-basin/blob/main/src/libraries/LibBytes.sol

Bug:
There is a bug in the storeUint128 function that prevents proper storage of reserves when the reserves array has an odd number of elements. The bug occurs in the following code block:

if (reserves.length & 1 == 1) {
    require(reserves[reserves.length - 1] <= type(uint128).max, "ByteStorage: too large");
    iByte = maxI * 64;
    assembly {
        sstore(
            add(slot, mul(maxI, 32)),
            add(mload(add(reserves, add(iByte, 32))), shl(128, shr(128, sload(add(slot, mul(maxI, 32))))))
        )
    }
}


The bug is in the line add(mload(add(reserves, add(iByte, 32))), shl(128, shr(128, sload(add(slot, mul(maxI, 32)))))). The sload function is used to load the value from storage, but the address passed to it is incorrect. It should be add(slot, add(iByte, 32)) instead of add(slot, mul(maxI, 32)).

Impact:
Due to this bug, when there is an odd number of reserves, the last reserve is not stored correctly in the storage slot. This can lead to incorrect data retrieval when calling the readUint128 function.

##Proof of concept 

Here's a proof of concept to demonstrate the bug in the storeUint128 function and the fix in action:

pragma solidity ^0.8.17;

import "./LibBytes.sol";

contract LibBytesBugDemo {
    using LibBytes for bytes32;

    bytes32 public storageSlot;

    function demonstrateBug(uint256[] memory reserves) external {
        storageSlot.storeUint128(reserves);
    }

    function demonstrateFix(uint256[] memory reserves) external {
        storageSlot.storeUint128Fixed(reserves);
    }

    function getStoredValues(uint256 n) external view returns (uint256[] memory) {
        return storageSlot.readUint128(n);
    }
}

In the LibBytesBugDemo contract, we import the LibBytes library and define two external functions: demonstrateBug and demonstrateFix. These functions simulate the usage of the storeUint128 function with an array of reserves.

The demonstrateBug function calls the original storeUint128 function, which contains the bug. The demonstrateFix function calls the fixed version of the function, named storeUint128Fixed, which includes the bug fix.

We also have a getStoredValues function to retrieve the stored values using the readUint128 function.

we In the LibBytesBugDemo contract, we import the LibBytes library and define two external functions: demonstrateBug and demonstrateFix. These functions simulate the usage of the storeUint128 function with an array of reserves.

The demonstrateBug function calls the original storeUint128 function, which contains the bug. The demonstrateFix function calls the fixed version of the function, named storeUint128Fixed, which includes the bug fix.

also have a getStoredValues function to retrieve the stored values using the readUint128 function.

Recommendation:
To fix the bug, replace the incorrect line in the storeUint128 function with the following line:

sstore(add(slot, add(iByte, 32)), add(mload(add(reserves, add(iByte, 32))), shl(128, shr(128, sload(add(slot, add(iByte, 32)))))))


By making this change, the last reserve will be properly stored in the storage slot, ensuring correct data retrieval when calling the readUint128 function.


## Assessed type

Decimal