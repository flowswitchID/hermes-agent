# #185: Well.sol contract allows anyone to add liquidity to tokens with fee-on-transfer by calling the addLiquidity function
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L392-L408


# Vulnerability details

## Impact

A malicious user can call the wrong function for adding liquidity for a pair with fee-on-transfer token(s). 
The reserves information maintained within the contract suffers from an inconsistency which can result in various miscalculations for liquidity providers.

## Proof of Concept 

The Well.sol contract maintains two functions for adding liquidity- addLiquidity() and addLiquidityFeeOnTransfer(). The former is meant for adding liquidity to tokens without fee on transfer whereas the latter is meant for tokens with fee on transfer.

However, anyone can call the addLiquidity function for a token with fee on transfer and the contract will not check for its validity. This will result in the contract not adjusting for the possibility of fee on transfer and the reserves information maintained in the contract to be incorrect.

This will also result in the liquidity provider receiving an incorrect number of LP tokens for their liquidity position.

1. A malicious user observes a liquidity pool with a fee on transfer token pair and calls the addLiquidity function instead of addLiquidityFeeOnTransfer.
2. The reserves are calculated incorrectly by the contract, which results in a higher number of shares being minted for the user.
3. The malicious user can redeem these LP tokens for a higher value than it is supposed to receive
4. Inconsistencies in the reserve information kept in contract state and the actual token balance of the contract results in incorrect calculations being done thereafter. 

## Tools Used

Manual Review

## Recommended Mitigation Steps

There are some solutions which can be explored:

1. Assume all tokens might have fee on transfer and check balance of tokens in the contract before and after transfer for all liquidity additions
2. Maintain a registry of liquidity pools with fee on transfer and dynamically choose the path.


## Assessed type

Token-Transfer