# #23: _notifyReward in `MultiFeeDistribution.sol` will skip reward periods causing loss for users
Labels: ['bug', '3 (High Risk)', 'satisfactory', 'sufficient quality report', ':robot:_primary', ':robot:_88_group', 'duplicate-126']
Accepted: False

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L1207


# Vulnerability details

## Impact
Skipped reward periods causing less rewards for users - High.

## Proof of Concept
The _notifyReward function does a storage update of the  `r.lastUpdateTime = block.timestamp`(https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L1207) without actually updating the reward. This will happen in functions like `vestTokens()` which call _notifyReward but do not call `_updateReward`. As a result the reward for the period between r.lastUpdateTime and block.timestamp will be skipped anytime `vestTokens()` is called.
## Root Cause 
lastUpdate time is set without updating the rewardPerTokenStored in _notifyReward:
https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/MultiFeeDistribution.sol#L1207
## Tools Used
Manual Review
## Recommended Mitigation Steps
Make sure to call _updateReward everytime _notifyReward is called.


## Assessed type

Other