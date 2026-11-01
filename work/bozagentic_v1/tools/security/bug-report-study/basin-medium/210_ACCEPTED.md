# #210: Well.sol#removeLiquidityImbalanced - Handling Excess Reserves in removeLiquidityImbalanced Function to Prevent Unnecessary Reverts
Labels: ['bug', '2 (Med Risk)', 'downgraded by judge', 'high quality report', 'satisfactory', 'sponsor confirmed', 'duplicate-191']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L562


# Vulnerability details

## Impact
The `removeLiquidityImbalanced` function in the Well.sol contract is vulnerable to a potential underflow. This could disrupt the contract's functionality and prevent users from removing liquidity in an imbalanced manner. Furthermore, the function does not appropriately handle cases where reserves can be greater than minted liquidity due to external factors like donations. This could lead to unnecessary reverts of legitimate `removeLiquidity` transactions.

## Proof of Concept
The issue is located in the `removeLiquidityImbalanced` function of the Well.sol contract, specifically at this line: [Well.sol#L562](https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L562).

The potential underflow occurs in the following line of code:

`lpAmountIn = totalSupply() - _calcLpTokenSupply(wellFunction(), reserves);`

In addition, the function doesn't handle the scenario where reserves can be greater than minted liquidity due to external factors like donations. This could lead to unnecessary reverts of legitimate `removeLiquidity` transactions.

## Tools Used
The code review and analysis were performed manually, without the use of any specific security tools.
## Recommended Mitigation Steps

To mitigate this issue, it is recommended to add a check to ensure `totalSupply()` is not less than the return value of `_calcLpTokenSupply`. If it is, `lpTokenSupply` should be set to `totalSupply()`. This change would make the function call complete successfully even when reserves can be greater than minted liquidity due to donations. Here is an example of how this could be implemented:

```jsx
uint256 lpTokenSupply = _calcLpTokenSupply(wellFunction(), reserves);
if (totalSupply() < lpTokenSupply) {
    lpTokenSupply = totalSupply();
}
lpAmountIn = totalSupply() - lpTokenSupply;
```

This change will prevent the underflow from happening and also account for the scenario where reserves are greater than the total supply of liquidity tokens. This allows the function to handle donations and similar scenarios without reverting legitimate `removeLiquidity` transactions.


## Assessed type

Math