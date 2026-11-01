# #21: An infinite loop in `MultifeeDistribution.sol` exit() function
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sponsor confirmed', 'sufficient quality report', ':robot:_primary', ':robot:_237_group', 'duplicate-20']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L1006


# Vulnerability details

## Impact
An infinite loop in the exit function will cause unexpected reverts - High
## Proof of Concept
In the exit function the `withdrawableBalance` is called. However a the for-loop in 
withdrawableBalance can be infinite:
```solidity
uint256 earned = _balances[user].earned;
        if (earned > 0) {
            uint256 length = _userEarnings[user].length;
            for (uint256 i; i < length; ) {
                uint256 earnedAmount = _userEarnings[user][i].amount;
                if (earnedAmount == 0) continue;
```
As the code above states if the earned amount for a current unlock time is 0 the continue keyword is used. However since there is no i++ this code will result in an infinite loop preventing users from withdrawing 
## Tools Used
Manual Review
## Recommended Mitigation Steps
Add i++


## Assessed type

Other