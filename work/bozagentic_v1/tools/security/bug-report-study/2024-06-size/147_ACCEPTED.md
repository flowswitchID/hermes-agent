# #147: A user might repay the wrong borrower.
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', 'upgraded by judge', ':robot:_29_group', 'duplicate-181']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Repay.sol#L46


# Vulnerability details

## Impact
A user might repay the wrong borrower and lose funds unexpectedly.

## Proof of Concept
When a user repays a loan, it just validates the loan is not repaid already.

```solidity
    function validateRepay(State storage state, RepayParams calldata params) external view {
        // validate debtPositionId
        if (state.getLoanStatus(params.debtPositionId) == LoanStatus.REPAID) {
            revert Errors.LOAN_ALREADY_REPAID(params.debtPositionId);
 }

        // validate msg.sender
        // N/A
 }

    function executeRepay(State storage state, RepayParams calldata params) external {
        DebtPosition storage debtPosition = state.getDebtPosition(params.debtPositionId);

        state.data.borrowAToken.transferFrom(msg.sender, address(this), debtPosition.futureValue);
        debtPosition.liquidityIndexAtRepayment = state.data.borrowAToken.liquidityIndex();
        state.repayDebt(params.debtPositionId, debtPosition.futureValue);

        emit Events.Repay(params.debtPositionId);
 }    
```

But after calling [executeLiquidateWithReplacement()](https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/LiquidateWithReplacement.sol#L149), the loan's borrower might be replaced and the user might repay for the wrong borrower.

Here is an example.

- A borrower Alice has a debt position that is liquidatable.
- So she calls `repay()` for her debt position.
- But before her transaction, `liquidateWithReplacement()` is called by a keeper. (It's not a front running. It's possible during the normal interactions.)
- Within `liquidateWithReplacement()`, her collateral has been transferred to the lender/protocol and the loan has a new borrower. As her original debt position has been liquidated, she doesn't need to repay that loan.
- But her `repay()` is executed and she loses funds after repaying for the wrong borrower.

## Tools Used
Manual Review

## Recommended Mitigation Steps
Recommending adding `borrower` param to [RepayParams](https://github.com/code-423n4/2024-06-size/blob/8850e25fb088898e9cf86f9be1c401ad155bea86/src/libraries/actions/Repay.sol#L14) struct and validating in `validateRepay()`.

```diff
 function validateRepay(State storage state, RepayParams calldata params) external view {
 // validate debtPositionId
 if (state.getLoanStatus(params.debtPositionId) == LoanStatus.REPAID) {
 revert Errors.LOAN_ALREADY_REPAID(params.debtPositionId);
 }

+        if (param.borrower ! = state.getDebtPosition(params.debtPositionId)) {
+            revert Errors.WRONG_BORROWER(params.debtPositionId);
+        }

 // validate msg.sender
 // N/A
 }
```


## Assessed type

Invalid Validation