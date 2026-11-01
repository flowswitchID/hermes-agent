# #169: [MEDIUM] MultiFlowPump.sol - Missing check for BLOCK_TIME == 0 could cause pool to be stuck
Labels: ['bug', '2 (Med Risk)', 'disagree with severity', 'low quality report', 'sponsor confirmed', 'unsatisfactory', 'duplicate-287']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/pumps/MultiFlowPump.sol#L39
https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/pumps/MultiFlowPump.sol#L61
https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/pumps/MultiFlowPump.sol#L113
https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/pumps/MultiFlowPump.sol#L252
https://github.com/code-423n4/2023-07-basin/blob/f15fe66d57c2f226c232685d16f297e54bcc0939/src/pumps/MultiFlowPump.sol#L299


# Vulnerability details

## Impact
The current implementation of the MultiFlowPump contract has an underlying issue due to the absence of a check for `BLOCK_TIME == 0`. This condition can lead to unexpected behavior in various functions that utilize `BLOCK_TIME` for calculations, such as the `update()` function. This issue can make the pools stuck in certain situations, causing disruption in the contract's functioning and potentially leading to loss of funds.

## Tools Used


Manual review.

## Recommended Mitigation Steps
Add a check for `BLOCK_TIME == 0` during the contract initialization (in the constructor). If `BLOCK_TIME` is found to be 0, the initialization should fail with an appropriate error message. This ensures that any contract instance will always have a non-zero `BLOCK_TIME`.


## Assessed type

Invalid Validation