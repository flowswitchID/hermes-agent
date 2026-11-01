# #223: Anyone can receive funds from the Well.sol contract, thus reducing the token/tokenLp ratio for users
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613


# Vulnerability details

## Impact
In Well.sol skim(), anyone can withdraw funds that are not in reserve by simply calling the function. Such funds may remain, for example, when transactions are rounded off.

To credit extra tokens, reserve[token] has sync(). However, you can programmatically track when unaccounted tokens appear and display them before they are credited to reserve[token].

It would be more logical not to give tokens to anyone, but to record unaccounted funds in reserve[token]. This will increase the number of tokens in relation to the lp token.

## Proof of Concept
1. Anyone monitors the appearance of unaccounted tokens. It is possible to keep track of the mempool to get ahead of their enrollment in reserve[token] (for example, via sync()).
2. Calls skim()
3. Tokens are not credited to reserve[token]. The token/tokenLp ratio is less than it could be.

## Tools Used
Manual review

## Recommended Mitigation Steps
add the onlyOwner modifier, or remove skim(), putting extra tokens in reserve[token].


## Assessed type

Context