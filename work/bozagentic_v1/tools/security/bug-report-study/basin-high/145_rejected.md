# #145: Potential draining Well via slippage imprecision and swapping the same token
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L186-L319


# Vulnerability details

## Impact

According to `Well.sol` comment:

```
        // Note: The rounding approach of the Well function determines whether
        // slippage from imprecision goes to the Well or to the User.
```

imprecision can either goes to the Well or User. In this scenario we will assume that Well function is defined in a way which slippage imprecision goes to the user.

The problem (potentially) occurs when user tries to swap the same token (from `token_X` to `token_X`). Since this is the same token, the `balanceof` and `reserves` should return 1:1 ratio. However, due to rounding approach, the slippage from imprecision may go to the user. Thus instead of 1:1 ratio, user would receive 1:(1 + rounding).



## Proof of Concept


According to `init` function - the Well cannot be filled with two, same tokens. However, there's no check in swap functions if user is not swapping the same token (`fromToken` == `toToken`)
The main issue with the current implementation is that every swap function allows to swap the same token, which, might lead to some unexpected behavior.

Linking this behaviour with rounding from slippage imprecision implies, that the same tokens (which should be calculated as 1:1 ration) may not be calculated as 1:1.




## Tools Used

Manual code review

## Recommended Mitigation Steps

Every swap function should revert when `fromToken` == `toToken`.



## Assessed type

Other