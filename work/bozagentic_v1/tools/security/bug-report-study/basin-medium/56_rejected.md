# #56: overflowing uint40 lastTimestamp 
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/pumps/MultiFlowPump.sol#L42


# Vulnerability details

## Impact
always revert when using this struct PumpState

## Proof of Concept

After a time, block.timestamp will be bigger than uint40, this will lead to overflowing lastTimestamp

## Tools Used
manual
## Recommended Mitigation Steps

use uint256 lastTimestamp, this way it will never overflow, because block.timestamp is uint256


## Assessed type

Other