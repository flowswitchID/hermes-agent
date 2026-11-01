# #277: Well.sol::addLiquidity() Unauthorized Liquidity Addition for Fee-on-Transfer Tokens
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L392-L408


# Vulnerability details

## Description
The `addLiquidity()` in the Well.sol contract allows any address to add liquidity to tokens with a fee-on-transfer mechanism. Although there is a another function available to add liquidity for Fee-on-transfer token name `addLiquidityFeeOnTransfer()`. However user can describe themselves as non fee-on-transfer token and can add feeless liquidity.

## Impact
Malicious actors can exploit the vulnerability to manipulate the composition of the liquidity pool. By adding fee-on-transfer tokens, they can disrupt the balance and dynamics of the pool, leading to market distortions and potentially harming other users and liquidity providers.

The inclusion of fee-on-transfer tokens without proper checks can result in inaccurate liquidity calculations. This can lead to incorrect issuance of LP tokens, creating confusion and inconsistencies in liquidity provisioning. It undermines the integrity and reliability of the protocol's liquidity management.

Legitimate liquidity providers are at risk of suffering financial losses due to unauthorized liquidity addition. The presence of fee-on-transfer tokens without proper authorization can impact the rewards and earnings of liquidity providers, affecting their incentives to participate and contribute to the protocol.

## Proof of Concept
a) A malicious user identifies a liquidity pool in the Well.sol contract that involves a pair of tokens, one of which is a fee-on-transfer token.
b) The malicious user takes advantage of the vulnerability by calling the addLiquidity function instead of the intended addLiquidityFeeOnTransfer function.
c) As a result, the contract calculates the reserves incorrectly, leading to an overestimation of the liquidity pool shares minted for the user.
d) The malicious user can now redeem these LP (liquidity provider) tokens for a higher value than they are supposed to receive based on the actual liquidity in the pool.
e) The inconsistencies between the reserve information stored in the contract and the actual token balances further compound the issue, leading to incorrect calculations and potentially distorting the overall state of the liquidity pool.

## Tools Used

## Recommended Mitigation Steps
Treat all tokens as if they might have a fee on transfer and perform a thorough check of the token balances in the contract before and after any liquidity addition transactions. By comparing the balances, we can ensure that the expected amount of tokens has been transferred and detect any discrepancies or unexpected fees. This diligent verification process helps maintain the integrity of the liquidity pool and prevents any potential exploits related to fee-on-transfer tokens.


## Assessed type

Invalid Validation