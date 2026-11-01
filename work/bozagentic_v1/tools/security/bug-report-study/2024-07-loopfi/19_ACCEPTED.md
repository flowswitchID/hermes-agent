# #19: Directly sending dust token amount will slow down distribution in `MultiFeeDistribution.sol`
Labels: ['bug', '3 (High Risk)', 'primary issue', 'satisfactory', 'selected for report', 'sponsor confirmed', 'sufficient quality report', 'upgraded by judge', ':robot:_primary', 'H-15']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L1208


# Vulnerability details

## Impact
While sending a small amount and calling getReward is a typical example of griefing which is normally considered Medium. Given the low cost of the attack and that no specific external conditions need to be met as well as the high impact for all the users of the protocol I consider it High severity.

## Proof of Concept
The _getReward function in `MultiFeeDistribution.sol` will call `_notifyUnseenReward` which which will execute the following:
```solidity
 uint256 unseen = IERC20(token).balanceOf(address(this)) - r.balance;
            if (unseen > 0) {
                _notifyReward(token, unseen);
            }
```
If a small amount of `token` is sent directly to the contract this will mean that the unseen amount will also be very small but greater than 0. This will lead to the execution of:
```solidity   
 r.rewardPerSecond = ((reward + leftover) * 1e12) / rewardsDuration;
```
`reward` will be the dust amount that was sent by the user. As a result the following changes to the reward distribution will be made:
```solidity
else {
            uint256 remaining = r.periodFinish - block.timestamp;
            uint256 leftover = (remaining * r.rewardPerSecond) / 1e12;
            r.rewardPerSecond = ((reward + leftover) * 1e12) / rewardsDuration;
        }

        r.lastUpdateTime = block.timestamp;
        r.periodFinish = block.timestamp + rewardsDuration;
        r.balance = r.balance + reward;
```
Consider the following scenario: 
Reward period starts at with r.balance = 1000 eth and rewardsDuration = 10 days.(For simplicity the example will be in days not in seconds).
9 days have passed and a user calls `getReward` so the accumulated reward from the vesting will be 900 eth. However a malicious user decides to send a small reward directly to the protocol for example 1 wei and they call get reward again:
r.leftover = 100eth
r.rewardPerSecond = (100eth(leftover)+1wei) / 10 days(rewards duration) = 10 eth a day
r.period finish = now +10 days 
As you can see simply by directly sending a small amount athe rewardPerSecond was decreased drastically and the vest is now much longer.
## Tools Used
Manual Review
## Recommended Mitigation Steps
`_notifyUnseenReward` should not be in functions without access control for thrusted protocol roles as griefing would always be possible. If you still want the unseen amount to be updated frequently consider value-weighted time additions to the vesting.


## Assessed type

Other