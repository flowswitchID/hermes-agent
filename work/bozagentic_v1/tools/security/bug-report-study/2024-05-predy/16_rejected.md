# #16: It is possible to block stablecoin (USDC, USDT) swaps in the UniswapSettlement contract
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_116_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/settlements/UniswapSettlement.sol#L47


# Vulnerability details

## Impact
The `UniswapSettlement` contract will not execute swaps with USDC and USDT tokens.

## Proof of Concept
In this report we'd like to escalate the bot finding L-01:
https://github.com/code-423n4/2024-05-predy/blob/main/4naly3er-report.md#l-1-approvesafeapprove-may-revert-if-the-current-approval-is-not-zero

Let's check the `swapExactOut` function in the `UniswapSettlement` contract:
```solidity
    function swapExactOut(
        address quoteToken,
        address,
        bytes memory data,
        uint256 amountOut,
        uint256 amountInMaximum,
        address recipient
    ) external override returns (uint256 amountIn) {
        ERC20(quoteToken).safeTransferFrom(msg.sender, address(this), amountInMaximum);
>>      ERC20(quoteToken).approve(address(_swapRouter), amountInMaximum);

        amountIn = _swapRouter.exactOutput(
            ISwapRouter.ExactOutputParams(data, recipient, block.timestamp, amountOut, amountInMaximum)
        );

>>      if (amountInMaximum > amountIn) {
            ERC20(quoteToken).safeTransfer(msg.sender, amountInMaximum - amountIn);
        }
    }
```
We can notice two things:
1. `amountInMaximum` is approved to the router
2. it is expected that in some swaps not all tokens will be consumed by the router

This means that a non-zero allowance may be left. This is unacceptable for USDC(USDT) tokens and the next swap will fail due to `approve` transaction revert.

Note, that you cannot swap 0 tokens in the Uniswap, so it won't be possible to approve 0 tokens with `swapExactIn`:
https://github.com/Uniswap/v3-core/blob/main/contracts/UniswapV3Pool.sol#L596-L603
```solidity
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external override noDelegateCall returns (int256 amount0, int256 amount1) {
>>      require(amountSpecified != 0, 'AS');
``` 

And even if somehow allowance was set to zero, an attacker can easily block the contract again.

Since the `UniswapSettlement` contract and stablecoins are widely used in the perp operations, we'd like to draw sponsor's attention to this issue and increase it's severity.

## Tools Used
Manual review

## Recommended Mitigation Steps
Set allowance to zero after the swap.


## Assessed type

DoS