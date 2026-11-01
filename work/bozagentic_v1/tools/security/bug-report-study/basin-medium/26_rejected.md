# #26: The `swapTo` function in `Well.sol` is susceptible to underflow occurrences.
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L264-L290


# Vulnerability details

## Impact
The parameter `amountOut` in the `swapTo` function has the potential to experience underflow.

## Proof of Concept
The `swapTo` function is utilized to exchange tokens with a specific `amountOut` and `maxAmountIn`.

Within this function, the calculation for `reserve[j]` is performed as follows:
`reserves[j] -= amountOut;`
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L264-L290
```
    function swapTo(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 maxAmountIn,
        uint256 amountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountIn) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);
        (uint256 i, uint256 j) = _getIJ(_tokens, fromToken, toToken);

        reserves[j] -= amountOut;
        uint256 reserveIBefore = reserves[i];
        reserves[i] = _calcReserve(wellFunction(), reserves, i, totalSupply());

        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.
        amountIn = reserves[i] - reserveIBefore;

        if (amountIn > maxAmountIn) {
            revert SlippageIn(amountIn, maxAmountIn);
        }

        _swapTo(fromToken, toToken, amountIn, amountOut, recipient);
        _setReserves(_tokens, reserves);
    }

```
In certain cases, the balance of the j-th token can exceed the corresponding `reserves[j]` and tokens can be transferred from the pool to the user.

If the value of `amountOut` exceeds the current value of `reserve[j]`, an underflow occurs, leading to unpredictable errors within the `wellFunction()`.

In the event of an underflow, `reserve[j]` will contain a significantly large amount, thereby resulting in potential errors.

Consequently, this could lead to a modification in the value of reserves, which may result in critical issues.

## Tools Used

## Recommended Mitigation Steps
To prevent underflow issues, it is advisable to add a require statement to verify that amountOut is not greater than reserves[j]. 
```
require(amountOut <= reserves[j], "Amount out exceeds reserves");
```
By including this require statement, the function will revert if the condition amountOut <= reserves[j] is not met, preventing any underflow errors.


## Assessed type

Under/Overflow