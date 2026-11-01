# #32: possible precision/rounding error in calcReserve() of ConstantProduct2.sol
Labels: ['invalid', '2 (Med Risk)', 'low quality report', 'nullified', 'withdrawn by warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ConstantProduct2.sol#L58
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/functions/ConstantProduct2.sol#L66


# Vulnerability details

## Impact
in calcReserve() of ConstantProduct2.sol, there is a divison before multiplication when calculating the reserve amount value. This can cause inaccurate calculations/ precision/rounding errors 

## Proof of Concept
```
    function calcReserve(
        uint256[] calldata reserves,
        uint256 j,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure override returns (uint256 reserve) {
        // Note: potential optimization is to use unchecked math here
        reserve = lpTokenSupply ** 2;
        reserve = LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1] * EXP_PRECISION);
    }
```

Now snippet for code in LibMath.sol, the liibrary from which roundUpDiv() logic is used. 
```
    function roundUpDiv(uint256 a, uint256 b) internal pure returns (uint256) {
        if (a == 0) return 0;
        return (a - 1) / b + 1;
    }
```

## Tools Used
vs code 

## Recommended Mitigation Steps
do the multiplication first 
```
    function calcReserve(
        uint256[] calldata reserves,
        uint256 j,
        uint256 lpTokenSupply,
        bytes calldata
    ) external pure override returns (uint256 reserve) {
        // Note: potential optimization is to use unchecked math here
        reserve = lpTokenSupply ** 2;
        reserve = EXP_PRECISION * LibMath.roundUpDiv(reserve, reserves[j == 1 ? 0 : 1]);
    }
```



## Assessed type

Math