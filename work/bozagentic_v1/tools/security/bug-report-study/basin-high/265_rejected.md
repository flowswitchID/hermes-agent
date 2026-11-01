# #265: Well.sol::swapFrom() Missing Fee-on-Transfer Token Check
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-276']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L186-L196


# Vulnerability details

## Description
The `swapFrom()` in the Well.sol contract does not include a check for fee-on-transfer tokens, as specified in the Nespac. The comment states that the check for fee-on-transfer tokens is performed in the `_setReserves()`, but checks are not implemented in the `_setReserves()`. This may result in incorrect behavior or potential vulnerabilities if fee-on-transfer tokens are used.

## Impact
The lack of proper checks can result in incorrect reserve balances, leading to mismatches between reported and actual token values. This can cause financial losses for liquidity providers, as well as discrepancies in tracking and reporting token balances, creating confusion and inconsistencies.

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L632-L637

## Tools Used
Manual Review

## Recommended Mitigation Steps
Add a proper checks to check if token is fee-on-transfer or not in `swapFrom()` or `_setReserves()` as specified in Netspec


## Assessed type

Invalid Validation