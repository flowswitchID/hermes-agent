# #62: mismatching in the indexes may cause the function `removeLiquidty` to act strange or even revert
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L473-L479
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L470
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L462


# Vulnerability details

## Impact

a check for the index to the both `tokenAmountsOut` and `minTokenAmountsOut` should be added in `removeLiquidity` function, because the function will make check for the if the `tokenAmountsOut < minTokenAmountsOut ` but the `tokenAmountsOut` may have less in index than the `minTokenAmountsOut` and this function will always revert due to mismatching in the indexes.

## Proof of Concept

check this line in `removeLiquidity` function

```solidity
 function removeLiquidity(
        uint256 lpAmountIn,
        uint256[] calldata minTokenAmountsOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256[] memory tokenAmountsOut) {
        ...
        for (uint256 i; i < _tokens.length; ++i) {
            //@audit should check for if the index are equals
            if (tokenAmountsOut[i] < minTokenAmountsOut[i]) {
                revert SlippageOut(tokenAmountsOut[i], minTokenAmountsOut[i]);
            }
        }
        ...
```

if the indexes of `tokenAmountsOut` is [1,2,3,4] and the `minTokenAmountsOut` is [1,2,3,4,5] then this loop will cause some mismatching in the logic function because of `tokenAmountsOut[4] > minTokenAmountsOut[5]` is possible or even the function may revert.

## Tools Used

manual review

## Recommended Mitigation Steps

recommend to add check for both indexes and make sure this mismatching not possible.

```solidity
require(tokenAmountsOut.length == minTokenAmountsOut.length)
```



## Assessed type

Other