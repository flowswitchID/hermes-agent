# #138: Issue: Lack of balance check could result in overdraft
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L774-L782


# Vulnerability details

## Impact: This issue could result in the from address losing gas fees without receiving any tokens in return, potentially causing a financial loss.

## Proof of Concept
The _safeTransferFromFeeOnTransfer function in its current form does not include a balance check for the from address before initiating a transfer. This could result in an "overdraft" situation where the transfer fails and the from address loses gas fees without receiving any tokens in return. To mitigate this issue, a check should be added to ensure that the from address has sufficient balance to cover the transfer amount before initiating the transfer.

```solidity
File: /src/Well.sol
  function _safeTransferFromFeeOnTransfer(
        IERC20 token,
        address from,
        uint256 amount
    ) internal returns (uint256 amountTransferred) {
        uint256 balanceBefore = token.balanceOf(address(this));
        token.safeTransferFrom(from, address(this), amount);
        amountTransferred = token.balanceOf(address(this)) - balanceBefore;
    }
```
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L774-L782

## Tools Used
  Manual review and chatgpt

## Recommended Mitigation:

```solidity
   function _safeTransferFromFeeOnTransfer(
        IERC20 token,
        address from,
        uint256 amount
    ) internal returns (uint256 amountTransferred) {
        require(token.balanceOf(from) >= amount, "Insufficient balance");
        uint256 balanceBefore = token.balanceOf(address(this));
        token.safeTransferFrom(from, address(this), amount);
        amountTransferred = token.balanceOf(address(this)) - balanceBefore;
    }
```
In this modified version of the function, a require statement has been added to ensure that the from address has sufficient balance to cover the transfer amount. The function will revert if the check fails, preventing the transfer from proceeding and avoiding any potential loss of gas fees.


## Assessed type

Other