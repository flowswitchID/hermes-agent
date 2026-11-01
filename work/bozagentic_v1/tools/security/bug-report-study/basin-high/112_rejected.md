# #112: MultiFlowPump.readTwaReserves will throw error when called and won't calculate time weighted average because of missing parameter
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L307 #L307
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L239 #L239


# Vulnerability details

## Impact
MultiFlowPump.readTwaReserves uses ICumulativePump.readTwaReserves interface. However, MultiFlowPump.readTwaReserves omitted the "data" parameter as in the interface. This would cause the MultiFlowPump.readTwaReserves to always throw an error when called. It won't be possible to determine the time-weighted-average reserves for a given liquidity pool.

This same bug is also in MultiFlowPump.readCumulativeReserves which uses ICumulativePump.readCumulativeReserves interface.


## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L307

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/pumps/ICumulativePump.sol#L31

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L280C14-L280C36

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/pumps/ICumulativePump.sol#L17


## Tools Used

## Recommended Mitigation Steps


## Assessed type

Error