# #241: First liquidity provider can break minting of shares
Labels: ['bug', '2 (Med Risk)', 'disagree with severity', 'sponsor acknowledged', 'unsatisfactory', 'duplicate-274']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L413-L444


# Vulnerability details

## Impact
The attack vector and impact is that users may not receive shares in exchange for their deposits if the total asset amount has been manipulated through a large “donation”.

## Proof of Concept
The attack vector and impact is that users may not receive shares in exchange for their deposits if the total asset amount has been manipulated through a large “donation”.

An attacker can exploit using these steps:
1. Create and add 1 wei tokens to liquidity. At this moment, attacker is minted 1 wei LP token.
2. Transfer large amount of tokens directly to the contract, such as 1e9. Since no new LP token is minted, 1 wei LP token worths 1e9 reserve tokens.
3. Normal users add liquidity to pool will revert, because of subtraction underflow if they add less than 1e9 reserve tokens.

```solidity
        lpAmountOut =
            _calcLpTokenSupply(wellFunction(), reserves) -
            totalSupply();
```

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L460-L491
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L392-L399

## Tools Used
Manual Review

## Recommended Mitigation Steps
You can use different approach of the lpAmountOut calculation


## Assessed type

Math