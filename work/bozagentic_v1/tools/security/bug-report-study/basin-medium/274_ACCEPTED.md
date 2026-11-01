# #274: Possible Issues Related to Well Initial State
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/BeanstalkFarms/Basin/blob/master/src/Well.sol#L413-L444


# Vulnerability details

## Description && Impact
After creating the Well contract, there will be no reserves in the initial state. Therefore it could lead to the following possible issues and the attackers can take advantage of them through front running.

1. Price manipulation attacks
When there is no liquid in the pool, the attacker can initialize the pool at any price. This could be an issue since some external parties may heavily rely on the pool's initial price. Therefore, it may cause unexpected damage to the project.

2. Inflation attacks
The attacker can take advantage of the possible truncation issue on calculating the shares and therefore inflating his shares by front running.
It could lead to asset loss for the first users who want to add liquidity to the pool. Considering the first liquidation are usually added  by the project, it may lead to assets loss to the project.


## Recommended Mitigation Steps

Recommend making an initial deposit. 


## Assessed type

Math