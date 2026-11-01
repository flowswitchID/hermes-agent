# #111: Missing check about fee-on-transfer tokens
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L186-L196
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L422-L434


# Vulnerability details

## Impact

The lack of the fee-on-transfer token check in the `Well` function results in unexpected losses. In the `swapFrom` function, the function parameter `amountIn` stands for the amount that transfers to the `Well` function. However, the actual received amount may be inconsistent with if the `fromToken` is a fee-on-transfer token.

A similar situation also exists in the `addLiquidity` function. If one of the tokens (or all of them) are fee-on-transfer tokens, the actual amount of token that `Well` received is inconsistent with the input parameter `tokenAmountsIn`.

This bug can result in financial loss of the protocol, thus we consider this a high-risk.

## Proof of Concept

```
## the addLiquidity function
function addLiquidity(
    uint256[] memory tokenAmountsIn,
    uint256 minLpAmountOut,
    address recipient,
    uint256 deadline
) external nonReentrant expire(deadline) returns (uint256 lpAmountOut) {
    lpAmountOut = _addLiquidity(tokenAmountsIn, minLpAmountOut, recipient, false);
}

## part of the _addLiquidity function
if (feeOnTransfer) {
    for (uint256 i; i < _tokens.length; ++i) {
        if (tokenAmountsIn[i] == 0) continue;
        tokenAmountsIn[i] = _safeTransferFromFeeOnTransfer(_tokens[i], msg.sender, tokenAmountsIn[i]);
        reserves[i] = reserves[i] + tokenAmountsIn[i];
    }
} else {
    for (uint256 i; i < _tokens.length; ++i) {
        if (tokenAmountsIn[i] == 0) continue;
        _tokens[i].safeTransferFrom(msg.sender, address(this), tokenAmountsIn[i]);
        reserves[i] = reserves[i] + tokenAmountsIn[i];
    }
}
```

Here we take [addLiquidity](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L422-L434) as an example, proper checks are lacking when attackers invoke the `addLiquidity` function with fee-on-transfer tokens.

Here is how we attack:
+ Assuming the `Well` contract is deployed with two types of token (i.e., fee-on-transfer token A and token B)
+ Bob deposits fee-on-transfer token A through the `addLiquidity` function instead of the `addLiquidityFeeOnTransfer` function.
+ Bob receives more lp tokens compared to the actual amount of the input token.

The `swapFrom` function is also vulnerable to this bug.

## Recommended Mitigation Steps

Replace all `safeTransferFrom` functions with the `_safeTransferFromFeeOnTransfer` function.


## Assessed type

Token-Transfer