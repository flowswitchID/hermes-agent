# #174: The `expire()` modifier is is useless because of just checkl `block.timestamp > deadline` and the `deadline` can be faked
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L193
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L789


# Vulnerability details

## Impact

It cause the `deadline` is useless 

## Proof of Concept

As we can see, the modifier is defined:
```solidity
modifier expire(uint256 deadline) {
        if (block.timestamp > deadline) {
            revert Expired();
        }
        _;
    }
```
It will check `block.timestamp > deadline` , but the `deadline ` is from user and the `deadline` can be faked, and the `deadline` parameter doesn't seem to play a role. Such `swapFrom()` function, the `deadline` parameter comes from the user, it has only passed through the expire modifier , and there is no other place/function to use it(`deadline`) later.
```solidity
function swapFrom(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountOut) {
        fromToken.safeTransferFrom(msg.sender, address(this), amountIn);
        amountOut = _swapFrom(fromToken, toToken, amountIn, minAmountOut, recipient);
    }
```
Thus, I consider the `deadline` is useless 
## Tools Used

vs code

## Recommended Mitigation Steps

Make parameter `deadline` useful or delete it if it is useless


## Assessed type

Error