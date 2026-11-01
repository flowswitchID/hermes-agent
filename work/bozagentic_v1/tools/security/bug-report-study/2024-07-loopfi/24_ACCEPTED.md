# #24: Users who turn ineligible will have their pending rewards stuck
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary', ':robot:_100_group']
Accepted: True

# Lines of code

https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/ChefIncentivesController.sol#L520


# Vulnerability details

## Impact
Pending rewards for ineligible uses will be unclaimable - High

## Proof of Concept
Users can withdraw their vested tokens from the `MultiFeeDistribution.sol` anytime. By doing this they can decrease their locked balances which is the main factor for their eligibility. However the only way a user can claim their pending rewards is through the `claim` function in `ChefIncentivesController.sol`. 
Because of the following check users who become ineligible will not be able to claim even their pending rewards which they are entitled to:
https://github.com/code-423n4/2024-07-loopfi/blob/57871f64bdea450c1f04c9a53dc1a78223719164/src/reward/ChefIncentivesController.sol#L520

## Tools Used
Manual Review
## Recommended Mitigation Steps
Whenever users withdraw from their locked balances call claim in the `ChefIncentivesController`


## Assessed type

Other