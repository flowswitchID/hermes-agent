# #20: An infinite loop in `MultiFeeDistribution.sol`  withdraw
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', 'edited-by-warden', ':robot:_237_group', 'H-14']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L555


# Vulnerability details

## Impact
An infinite loop will block the withdraw process - High.

## Proof of Concept
In the MultiFeeDistribution.sol the `withdraw` function will start going through user's locked amounts if they do not have enough unlocked to cover their withdraw request:
```solidity 
  if (amount <= bal.unlocked) {
            bal.unlocked = bal.unlocked - amount;
        } else {
            uint256 remaining = amount - bal.unlocked;
            if (bal.earned < remaining) revert InvalidEarned();
            bal.unlocked = 0;
            uint256 sumEarned = bal.earned;
            uint256 i;
            for (i = 0; ; ) {
                uint256 earnedAmount = _userEarnings[_address][i].amount;
                if (earnedAmount == 0) continue;
```
However as you can see i will stay 0 and the following check will execute:
```solidity 
  if (earnedAmount == 0) continue;
```
the continue will start a new iteration of the loop however i will still be 0 and this loop will never end. As a result claiming from locked amounts with penalty will not be possible.

## Tools Used
Manual Review
## Recommended Mitigation Steps
Rewrite the code the following way:
```solidity 
  if (earnedAmount == 0) {
i++;
continue;
}
```





## Assessed type

Loop