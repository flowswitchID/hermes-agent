# #229: Not all features of the protocol are used
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L1


# Vulnerability details

## Impact

In current implementation The protocol won't be so popular as it can be. This is because a lot of transactions uses flash loan. 
In current implementation flash loan impossible, because user must transfer his funds at the first.
This leads to small amount of liquidity, because liquidity providers will select protocols which help to earn money in all possible ways, not just by the usual exchange. 

## Proof of Concept
Let's consider `Well` contract and `swapFrom` or `swapTo` functions.
Both these contracts at the first transfers tokens from `msg.sender` to `Well` contract. So if user wants to acquire a lot of tokens in a single transaction he must provide a lot of another tokens. 
This is not convenient for using the Basin in arbitrage.

## Tools Used

Manual review

## Recommended Mitigation Steps

Add function to take flash loan. This will help liquidity provider to get more fees and users to get more proffit.


## Assessed type

Other