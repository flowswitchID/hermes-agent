# #137: Possible to mint 0 Liquidity tokens
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L436-L439
https://github.com/code-423n4/2023-07-basin/blob/main/src/functions/ConstantProduct2.sol#L49-L54


# Vulnerability details

## Impact
User may lost his tokens if he'll provide liquidity for only one token, and second tokens amount will be 0.


## Proof of Concept
In `Well` exists function `_addLiquidity`, which calls `IWellFunction.calcLpTokenSupply`, this function returns actual amount of Liquidity tokens, but for example, if consider `ConstantProduct2` as `wellFunction` we can notice -- if one of reserves is 0, then total LP amount will be 0 -- for example due to external implementation.
So, user pass money for only one side, and might get zero liquidity. This case might be successfully if `minLpAmountOut` will be set as 0, because condition:
```solidity
        if (lpAmountOut < minLpAmountOut) {
            revert SlippageOut(lpAmountOut, minLpAmountOut);
        }

```
where `lpAmountOut = minLpAmountOut = 0` will skip this revert and transaction will pass.

## Tools Used

Manual review

## Recommended Mitigation Steps

There is no any logical explanation of desire to mint 0 liquidity tokens, so forbid to mint zero tokens.

It's similar to just send tokens to contract and call sync then.


## Assessed type

Other