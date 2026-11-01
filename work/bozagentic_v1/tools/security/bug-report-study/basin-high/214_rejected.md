# #214: Well.sol::skim() anyone can transfer excess funds to their account.
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/Well.sol#L603-L613


# Vulnerability details

## Description
The `skim()` is designed to transfer excess tokens held by the contract to a specified recipient. However, it lacks proper access control checks, allowing any user to initiate the transfer of excess tokens, regardless of ownership. This presents a critical security vulnerability where an attacker can exploit the function to transfer tokens belonging to other users to their own account, leading to unauthorized token transfers and potential financial loss.

## Impact
High because by exploiting this vulnerability, an attacker can initiate unauthorized transfers of excess tokens belonging to arbitrary users to their own account. This unauthorized token transfer can lead to the depletion of user balances, disruption of token economy, and irreparable damage to the trust and confidence users place in the contract and its associated token system.

## Proof of Concept
https://gist.github.com/0xBugBuster/1fc01c234e312b82f27dd67ebf9d0e4c

## Step to reproduce
Copy the code from above gist, paste and save it to existing `test` directory and run it with following command.
`forge test --match-path test/Test.Skim.t.sol -vvv`

## Tools Used
Manual Review, Foundry for PoC

## Recommended Mitigation Steps
Modify the `skim()` to include a check that keeps track of the excess tokens of each user and verifies the ownership before executing any transfers. Implement a mechanism to store and update the excess token balances associated with each user within the contract.

When a user calls the `skim()`, compare the `msg.sender()` with the user's address whose excess tokens are being transferred. Only allow the transfer if `msg.sender()` matches the owner of the excess tokens. Otherwise, reject the transfer and emit an appropriate error message.


## Assessed type

Access Control