# #72: Incorrect Reserve Capping in MultiFlowPump Contract
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L199


# Vulnerability details

##Description

In the _capReserve function, there is a logical error in the condition for checking if the reserve value is greater than the maximum reserve. The incorrect condition causes the reserve value to be capped even when it is within the allowed range, leading to incorrect calculations of geometric mean and cumulative reserves.

#Affectd function
_capReserve

## Impact
Incorrect Geometric Mean: Capping the reserve values incorrectly can lead to incorrect calculations of the geometric mean. This can affect the accuracy of the EMA (Exponential Moving Average) calculations, which are used for instantaneous reserve queries.

Incorrect Cumulative Reserves: The bug can also impact the calculation of cumulative reserves, leading to incorrect values. Cumulative reserves are used for SMA (Simple Moving Average) reserve queries.

Data Inconsistency: The incorrect reserve calculations can result in inconsistent data across different queries and calculations, leading to incorrect decision-making and potential vulnerabilities in the system.

## Proof of Concept
pragma solidity ^0.8.17;

import "truffle/Assert.sol";
import "../contracts/MultiFlowPump.sol";

contract MultiFlowPumpTest {
    MultiFlowPump pump;

    function beforeEach() public {
        // Deploy the MultiFlowPump contract with initial parameters
        pump = new MultiFlowPump(ABDKMathQuad.fromUInt(10), ABDKMathQuad.fromUInt(10), 1, ABDKMathQuad.fromUInt(0.5));
    }

    function testUpdate() public {
        // Initialize reserves with 10 and update with 20
        uint256[] memory reserves = new uint256[](1);
        reserves[0] = 10;
        pump.update(reserves, "");

        reserves[0] = 20;
        pump.update(reserves, "");

        // Read the instantaneous reserves
        uint256[] memory instantaneousReserves = pump.readLastInstantaneousReserves(address(this));

        // Assert the expected value
        Assert.equal(instantaneousReserves[0], 20, "Incorrect instantaneous reserves");
    }
}

In this test, we initialize the reserves with a value of 10 and then update it to 20. We then read the instantaneous reserves and assert that the value matches the expected result. However, due to the bug in the _capReserve function, the instantaneous reserves may be capped to an incorrect value.

## Tools Used
truffle

## Recommended Mitigation Steps


To fix the bug, we can modify the _capReserve function as follows:

function _capReserve(
    bytes16 lastReserve,
    bytes16 reserve,
    bytes16 blocksPassed
) internal pure returns (bytes16 cappedReserve) {
    // Reserve decreasing (lastReserve > reserve)
    if (lastReserve.cmp(reserve) == 1) {
        bytes16 minReserve = lastReserve.sub(blocksPassed.mul(LOG_MAX_DECREASE));
        // if reserve < minimum reserve, set reserve to minimum reserve
        if (reserve.cmp(minReserve) == -1) reserve = minReserve;
    }
    // Reserve increasing or staying the same.
    else {
        bytes16 maxReserve = lastReserve.add(blocksPassed.mul(LOG_MAX_INCREASE));
        // If reserve > maximum reserve, set reserve to maximum reserve
        if (reserve.cmp(maxReserve) == 1) reserve = maxReserve;
    }
    cappedReserve = reserve;
}



## Assessed type

Invalid Validation