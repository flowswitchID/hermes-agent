# #5: Possible approval revert for USDT token
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', 'edited-by-warden', ':robot:_116_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-05-predy/blob/a9246db5f874a91fb71c296aac6a66902289306a/src/settlements/UniswapSettlement.sol#L38-L56


# Vulnerability details

## Impact
When the contract wants to approve USDT tokens for uniswap v3 pool in order to buy some base tokens, eg, WETH, `approve` might be reverted. This will cause `trade` failure. 

## Proof of Concept
In the predy contract, if we want to open one perp or sqrt perp position, sometimes we need to buy some base tokens. To make sure the exact output token amount, `amountInMaximum` is usually than the actual `amountIn`. Before we interact with Uniswap Pool, we need to approve `amountInMaximum` amount of quote tokens to Uniswap V3 pool.

```javascript
    function swapExactOut(
        address quoteToken,
        address,
        bytes memory data,
        uint256 amountOut,
        uint256 amountInMaximum,
        address recipient
    ) external override returns (uint256 amountIn) {
        ERC20(quoteToken).safeTransferFrom(msg.sender, address(this), amountInMaximum);
        ERC20(quoteToken).approve(address(_swapRouter), amountInMaximum);

        amountIn = _swapRouter.exactOutput(
            ISwapRouter.ExactOutputParams(data, recipient, block.timestamp, amountOut, amountInMaximum)
        );

        if (amountInMaximum > amountIn) {
            ERC20(quoteToken).safeTransfer(msg.sender, amountInMaximum - amountIn);
        }
    }
```
The vulnerability is that USDT token has one approval race condition protection. From the readme.txt, we can see that we wish to support USDT token, and USDT token does not allow to approve when the `allowance` is not zero.
For example, when we execute one order, we buy some WETH tokens with USDT tokens, there might be some left `allowance[Uniswapv3settlement][uniswapV3pool]`. When we execute another other, and we want to approve with one new value, this operation will be reverted.

```sol
    function approve(address _spender, uint _value) public onlyPayloadSize(2 * 32) {

        // To change the approve amount you first have to reduce the addresses`
        //  allowance to zero by calling `approve(_spender, 0)` if it is not
        //  already 0 to mitigate the race condition described here:
        //  https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
        require(!((_value != 0) && (allowed[msg.sender][_spender] != 0)));

        allowed[msg.sender][_spender] = _value;
        Approval(msg.sender, _spender, _value);
    }
```
## Tools Used
Manual

## Recommended Mitigation Steps
```diff
diff --git a/src/settlements/UniswapSettlement.sol b/src/settlements/UniswapSettlement.sol
index 7bb011a..6c8c63b 100644
--- a/src/settlements/UniswapSettlement.sol
+++ b/src/settlements/UniswapSettlement.sol
@@ -44,6 +44,7 @@ contract UniswapSettlement is ISettlement {
         address recipient
     ) external override returns (uint256 amountIn) {
         ERC20(quoteToken).safeTransferFrom(msg.sender, address(this), amountInMaximum);
         ERC20(quoteToken).approve(address(_swapRouter), amountInMaximum);
 
         amountIn = _swapRouter.exactOutput(
@@ -53,6 +54,7 @@ contract UniswapSettlement is ISettlement {
         if (amountInMaximum > amountIn) {
             ERC20(quoteToken).safeTransfer(msg.sender, amountInMaximum - amountIn);
         }
+        ERC20(quoteToken).approve(address(_swapRouter), 0);
     }

```










## Assessed type

DoS