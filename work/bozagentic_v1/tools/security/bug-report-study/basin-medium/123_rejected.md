# #123: Imbalanced liquidity token amounts can allow users to very easily manipulate prices
Labels: ['bug', '2 (Med Risk)', 'downgraded by judge', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L392


# Vulnerability details

## Impact
`addLiquidity` function can make price manipulations easy with certain `Well` and `wellFunction` eg. `Well` that would try to implement Uniswap V3.

## Proof of Concept
Consider a Uniswap V3 implementation on Basin. Let's assume that we are making a transaction at a price with very high liquidity.
Usually it would require for users to swap a very large amount to manipulate price (due to the high liquidity); however, as `addLiquidty()` allows users to specify custom `tokenAmountsIn`, a user can arbitrarily increase the reserve of a specific token, therefore skewing the price.

## Recommended Mitigation Steps
Add a `verifyTokenInAmounts()` function which allows the `wellFunction` to verify `tokenAmountsIn`. This can of course be left empty if the wellFunction writer wishes.
E.g. a Uniswap V3-like implementation will be able to make sure that the ratios of `tokenAmountsIn` is correct. If not, it can revert.


## Assessed type

Uniswap