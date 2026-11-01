# #8: Incorrect collateral calculation
Labels: ['bug', '3 (High Risk)', 'insufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_25_group']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/LeverageZapRouterBase.sol#L142-L144
https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/LeverageZapRouterBase.sol#L188
https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/EbtcLeverageZapRouter.sol#L398-L400
https://github.com/code-423n4/2024-06-badger/blob/9173558ee1ac8a78a7ae0a39b97b50ff0dd9e0f8/ebtc-zap-router/src/EbtcLeverageZapRouter.sol#L181


# Vulnerability details

## Impact
Collateral is incorrectly calculated, resulting in incorrect parameters for cdp that underestimate the user's total collateral balance. Results in loss of funds for the user as cdps with adequate collateral can be deemed unhealthy, and are later redeemed for a lesser amount of collateral than deposited. 

## Proof of Concept
When depositing margin either by adjusting an existing cdp or opening a new cdp, the steth amount is transferred in and the balance change in steth tokens is used to determine the margin change of the cdp.

However, this margin change is then converted again into shares, and the values are treated like they are eth rather than steth tokens as the `steth.getSharesByPooledEth` function is called on them. As a result, the actual collateral amount recorded is an underestimate since this function is monotonically decreasing as the amount of pooled eth goes up. 

## Tools Used
Manual review.

## Recommended Mitigation Steps
Use the margin change directly when calculating the collateral of cdps, rather than passing this value through `steth.getSharesByPooledEth`


## Assessed type

ERC20