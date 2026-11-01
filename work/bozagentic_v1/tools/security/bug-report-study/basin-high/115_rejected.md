# #115: The `Well` contract is vulnerable to front-running attack
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-291']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L352-L377
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L603-L613


# Vulnerability details

In the `Well` contract, the `Well:shift` function is utilized to optimize multi-hop swap. However, if users call the function with multiple individual transactions, the atomicity of the multi-hop swap is broken. More specifically, if the previous router (e.g., `Well1`) transfers tokens to the current router (e.g., `Well2`), the transaction invoking `shift` can be front-run by others, since there is no identification about the current user.

This situation also exists in the `Well:skim()` function.

## Impact

Attackers can front-run careless users and cause financial loss to users.

## Proof of Concept

```
function shift(
    IERC20 tokenOut,
    uint256 minAmountOut,
    address recipient
) external nonReentrant returns (uint256 amountOut) {
    IERC20[] memory _tokens = tokens();
    uint256[] memory reserves = new uint256[](_tokens.length);

    // Use the balances of the pool instead of the stored reserves.
    // If there is a change in token balances relative to the currently
    // stored reserves, the extra tokens can be shifted into `tokenOut`.
    for (uint256 i; i < _tokens.length; ++i) {
        reserves[i] = _tokens[i].balanceOf(address(this));
    }
    uint256 j = _getJ(_tokens, tokenOut);
    amountOut = reserves[j] - _calcReserve(wellFunction(), reserves, j, totalSupply());

    if (amountOut >= minAmountOut) {
        tokenOut.safeTransfer(recipient, amountOut);
        reserves[j] -= amountOut;
        _setReserves(_tokens, reserves);
        emit Shift(reserves, tokenOut, amountOut, recipient);
    } else {
        revert SlippageOut(amountOut, minAmountOut);
    }
}
```

As shown in the [Well:shift](https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L352-L377) function, anyone can withdraw the extra capital in the pool.

Here is how we attack:
+ Assuming Bob is going to conduct a multi-hop swap, he first swaps WETH to DAI from `Well1` and transfers all DAI to `Well2`. Note that this is an alone transaction.
+ Now Bob invokes the `Well2:shift` function to swap all DAI to USDC, with submitting another transaction.
+ Alice notices the transaction proposed by Bob and submits another transaction to front-run Bob.
+ Alice receives all USDC token belonging to Bob and Bob fail with his transaction.

## Recommended Mitigation Steps

Ensuring the caller of the `Well:shift` is a contract, to ensure the atomicity of multi-hop swap.


## Assessed type

Other