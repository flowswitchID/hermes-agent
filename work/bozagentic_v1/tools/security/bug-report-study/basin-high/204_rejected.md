# #204: cumulativeReserves can be incorrect
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'duplicate-287']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L123-L124


# Vulnerability details

## Impact
Detailed description of the impact of this finding.

Well updates the pump each time someone interacts with the well. update() calculates the mev resistant values, one of which is the cumulativeReserves.
If the update() function is called twice or more times in a single block, and the reserves change in-between each call to update(), readLastCumulativeReserves() will return incorrect, outdated cumulative reserves.

## Proof of Concept
Provide direct links to all referenced code in GitHub. Add screenshots, logs, or any other relevant proof that illustrates the concept.

1. update() is called multiple times in 1 block. the reserves have changed, but the block.timestamp stays the same, so the pumpState.lastReserves[i] and pumpState.emaReserves[i] are calculated correctly, according to our new reserves, but pumpState.cumulativeReserves[i] are not, because the calculation involves the deltaTimestampBytes, which is 0.
2. A user (or well), then calls readLastInstantaneousReserves() and the returned value is outdated, even though the lastReserves and emaReserves values are updated.

The incorrect value can persist for multiple blocks, as long as the well doesn't call the update() function or readCumulativeReserves().

## Tools Used
manual review
## Recommended Mitigation Steps
Handle the case where the reserves change, but block.timestamp is the same as the previous update(). Check if the current block is the same as the previous one, if it is, then maybe multiply by 1 instead of deltaTimestampBytes (which is 0).


## Assessed type

Other