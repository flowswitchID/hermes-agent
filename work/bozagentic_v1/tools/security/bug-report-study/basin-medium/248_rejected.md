# #248: Subsequent liquidity providers will suffer from the loss of funds
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413-L444
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L49-L54


# Vulnerability details

## Impact
When adding liquidity, lpAmountOut is calculated using the formula: _calcLpTokenSupply(wellFunction(), reserves) - totalSupply().

function _calcLpTokenSupply(
    Call memory _wellFunction,
    uint256[] memory reserves
) internal view returns (uint256 lpTokenSupply) {
    lpTokenSupply = IWellFunction(_wellFunction.target).calcLpTokenSupply(reserves, _wellFunction.data);
}

function calcLpTokenSupply(
    uint256[] calldata reserves,
    bytes calldata
) external pure override returns (uint256 lpTokenSupply) {
    //uint256 constant EXP_PRECISION = 1e12;
    lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt();
}

It all depends on lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt(). Based on this, it is clear that the more reserves, the less lpAmountOut tokens the user will receive. This represents the non-linear size of lpAmountOut as a function of reserves.

## Proof of Concept
Initial data:
reserves[0] = 10
reserves[1] = 20
sqrt(10*20*10e12) = 14 142 135

User 1 adds:
reserves[0] + 10
reserves[1] + 10
sqrt(20*30*10e12) = 24494897

User 2 adds:
reserves[0] + 10
reserves[1] + 10
sqrt(30*40*10e12) = 34641016

User 3 adds:
reserves[0] + 10
reserves[1] + 10
sqrt(40*50*10e12) = 44,721,359

Users added the same number of tokens. However,
user 1:
lpTokenSupply = 10,352,762
user 2:
lpTokenSupply = 10,146,119
user 3:
lpTokenSupply = 10,080,343

## Tools Used
Manual review

## Recommended Mitigation Steps
Add coefficients in lpTokenSupply = (reserves[0] * reserves[1] * EXP_PRECISION).sqrt() for a linear relationship with reserves


## Assessed type

Context