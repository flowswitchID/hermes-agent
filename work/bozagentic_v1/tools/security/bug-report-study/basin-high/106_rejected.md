# #106: SwapTo not check transferIn amount, so feeOnTransfer token will run out of the well
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L296-L306


# Vulnerability details

## Impact

The swapTo function calculates the reserve in advance according to the parameters and then extracts the token from the user. The problem is that it does not check whether the amount transferred is correct. 
For feeOnTransfer tokens, well will receive fewer than expected tokens, which will eventually run out of well.

## Proof of Concept

```solidity
    function _swapTo(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 amountOut,
        address recipient
    ) internal {
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn);
        toToken.safeTransfer(recipient, amountOut);
        emit Swap(fromToken, toToken, amountIn, amountOut, recipient);
    }
```

As you can see from the code, the well normally updates the reserve according to the parameters, but at the end does not check that the transfer amount is correct.
In this way, users transferIn feeOnToken below actual value to arbitrage. And for other staking users, when withdraw LP, well has no ability to pay due to pool imbalance, first come, first served, resulting in a run bank.

## Tools Used

Manual review

## Recommended Mitigation Steps

Check the actual amount transferred



## Assessed type

Token-Transfer