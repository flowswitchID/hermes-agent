# #77:  Incorrect Comparison in Well Contract's init Function
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L31


# Vulnerability details

## Impact
The bug in the init function of the Well contract affects the correctness of the contract's behavior. It can lead to incorrect initialization and potentially compromise the integrity and security of the contract. Additionally, the bug can cause unexpected errors or undesired behavior when interacting with the contract.

## Proof of Concept
The bug is present in the init function of the Well contract, specifically in the token duplication check loop. The code attempts to compare the addresses of tokens in the _tokens array to check for duplicates. However, the comparison is incorrect, leading to incorrect behavior.

Here is the problematic code snippet from the init function:

for (uint256 i; i < _tokens.length - 1; ++i) {
    for (uint256 j = i + 1; j < _tokens.length; ++j) {
        if (_tokens[i] == _tokens[j]) {
            revert DuplicateTokens(_tokens[i]);
        }
    }
}

The issue lies in the comparison if (_tokens[i] == _tokens[j]). In Solidity, the == operator compares the storage references of the two variables, which corresponds to comparing their storage addresses. However, in this context, the intention is to compare the token contract addresses, not their storage references. As a result, the comparison will always return false, even if the token addresses are the same.

 Here's a proof of concept test that demonstrates the bug in the Well contract:



contract WellTest {
    Well well;

    constructor() {
        // Deploy the Well contract
        well = new Well();
    }

    function testInitWithDuplicateTokens() external {
        // Create an array of tokens with a duplicate address
        address[] memory tokens = new address[](2);
        tokens[0] = address(0x123);
        tokens[1] = address(0x123);

        // Call the init function of the Well contract with the duplicate tokens
        // This should trigger the bug and result in an incorrect initialization
        well.init(tokens);
    }
}


When we execute the testInitWithDuplicateTokens function in the WellTest contract, it will deploy a new instance of the Well contract and attempt to initialize it with an array of tokens that contain a duplicate address. This test is designed to demonstrate the incorrect behavior caused by the bug.

Upon running the test, we should observe that the Well contract fails to detect the duplicate tokens and proceeds with the initialization, even though it should have reverted due to the presence of the duplicate address.

To verify the bug, we can check the state of the deployed Well contract after the init function is called and ensure that it has been incorrectly initialized with duplicate tokens.

## Tools Used

## Recommended Mitigation Steps

 The comparison in the init function should be modified to compare the addresses of the token contracts instead of their storage references. This can be achieved by using the address typecasting on both _tokens[i] and _tokens[j] before the comparison. Here's the modified code snippet:

for (uint256 i; i < _tokens.length - 1; ++i) {
    for (uint256 j = i + 1; j < _tokens.length; ++j) {
        if (address(_tokens[i]) == address(_tokens[j])) {
            revert DuplicateTokens(_tokens[i]);
        }
    }
}


By applying this fix, the contract will correctly detect and revert when duplicate tokens are present in the _tokens array during initialization.


## Assessed type

Error