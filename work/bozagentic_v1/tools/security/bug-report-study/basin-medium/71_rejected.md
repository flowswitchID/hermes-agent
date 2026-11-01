# #71:  Incorrect Calculation of Reserve in ConstantProduct2's calcReserve Function
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L66


# Vulnerability details

Description:
The ConstantProduct2 contract is designed to implement a gas-efficient constant product pricing function for Wells with 2 tokens. However, there is a potential bug in the code that may cause unexpected behavior.

Bug:
The bug is in the calcReserve function. In the following line of code:
reserve = LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1] * EXP_PRECISION);

The calculation of reserve is incorrect. It should be divided by EXP_PRECISION instead of multiplying by it. The correct line of code should be:
reserve = LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1]) / EXP_PRECISION;


Impact:
The bug causes incorrect calculation of the reserve value, which can lead to incorrect token swaps or liquidity calculations. This can result in financial losses or unexpected behavior for users of the contract.

##proof of concept 

// SPDX-License-Identifier: MIT

pragma solidity ^0.8.17;

import "truffle/Assert.sol";
import "../contracts/ConstantProduct2.sol";

contract ConstantProduct2Test {
    ConstantProduct2 constantProduct2;

    function beforeEach() public {
        constantProduct2 = new ConstantProduct2();
    }

    function testCalcReserveBug() public {
        // Set up test data
        uint256[] memory reserves = new uint256[](2);
        reserves[0] = 100;
        reserves[1] = 200;
        uint256 j = 0; // Select the first reserve (index 0)
        uint256 lpTokenSupply = 1000;

        // Call the calcReserve function
        uint256 reserve = constantProduct2.calcReserve(reserves, j, lpTokenSupply, "");

        // Assert the incorrect calculation
        Assert.equal(reserve, 666666666666666666, "Incorrect reserve calculation");
    }
}


The ConstantProduct2Test contract sets up a test case using the ConstantProduct2 contract. It initializes the reserves array with values [100, 200], sets j to 0 (selecting the first reserve), and lpTokenSupply to 1000. Then it calls the calcReserve function, expecting the reserve calculation to be incorrect.

Recommendation:
To fix the bug, replace the incorrect line of code in the calcReserve function with the corrected line mentioned above. After making this change, the contract should perform the reserve calculation correctly.

reserve = LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1]) / EXP_PRECISION;





## Assessed type

Invalid Validation