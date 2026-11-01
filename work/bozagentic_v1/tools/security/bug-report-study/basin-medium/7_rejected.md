# #7: staticall success value not checked
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibContractInfo.sol#L53


# Vulnerability details

## Impact
Any error on the call could make the function enter in undefined behavior given the fact that it will return a `decimals` value from the variable `data`, whose value is undefined upon a `staticall` error.

## Proof of Concept
```solidity
function getDecimals(address _contract) internal view returns (uint8 decimals) {
        (bool success, bytes memory data) = _contract.staticcall(abi.encodeWithSignature("decimals()"));
        // there is no check for success == true

        decimals = success ? abi.decode(data, (uint8)) : 18; // default to 18 decimals
                                          ^-------------------------------------------------- HERE
}
```

## Tools Used
Manual analysis

## Recommended Mitigation Steps
Check the call to be made correctly with the `success` variable


## Assessed type

Invalid Validation