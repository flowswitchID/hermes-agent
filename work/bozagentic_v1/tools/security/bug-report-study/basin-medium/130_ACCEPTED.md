# #130: possible div by zero can cause panic error in calcLPTokenUnderlying() of ProportionalLPToken2.sol 
Labels: ['invalid', '2 (Med Risk)', 'low quality report', 'nullified', 'primary issue', 'withdrawn by warden']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ProportionalLPToken2.sol#L15


# Vulnerability details

## Impact
in the external function calcLPTokenUnderlying() all args required for the calculation logic performed is supplied via arguments, the 'lpTokenSupply' argument supplied can be zero, this causing the function to revert due to a possible division by zero. 

## Proof of Concept
```
abstract contract ProportionalLPToken2 is IWellFunction {
    function calcLPTokenUnderlying(
        uint256 lpTokenAmount,
        uint256[] calldata reserves,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure returns (uint256[] memory underlyingAmounts) {
        underlyingAmounts = new uint256[](2);
        underlyingAmounts[0] = lpTokenAmount * reserves[0] / lpTokenSupply;
        underlyingAmounts[1] = lpTokenAmount * reserves[1] / lpTokenSupply;
    }
}
```

## Tools Used
vs code 
## Recommended Mitigation Steps
it is best practice to add checks/conditions against the denominator being a zero value when doing divisions. 
```
abstract contract ProportionalLPToken2 is IWellFunction {
    function calcLPTokenUnderlying(
        uint256 lpTokenAmount,
        uint256[] calldata reserves,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure returns (uint256[] memory underlyingAmounts) {
        if( lpTokenSupply > 0 ) {
         underlyingAmounts = new uint256[](2);
         underlyingAmounts[0] = lpTokenAmount * reserves[0] / lpTokenSupply;
         underlyingAmounts[1] = lpTokenAmount * reserves[1] / lpTokenSupply;
        }
    }
}
```
 
OR 


```
abstract contract ProportionalLPToken2 is IWellFunction {
    function calcLPTokenUnderlying(
        uint256 lpTokenAmount,
        uint256[] calldata reserves,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure returns (uint256[] memory underlyingAmounts) {
        require(lpTokenSupply > 0, "lpTokenSupply is 0");
        underlyingAmounts = new uint256[](2);
        underlyingAmounts[0] = (lpTokenAmount * reserves[0]) / lpTokenSupply;
        underlyingAmounts[1] = (lpTokenAmount * reserves[1]) / lpTokenSupply;
    }
}
```





## Assessed type

Math