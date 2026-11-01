# #107: ProportionalLPToken2.calcLPTokenUnderlying will throw error when called because of incomplete interface implementation
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ProportionalLPToken2.sol#L15C4-L24C6 #L15


# Vulnerability details

## Impact
ProportionalLPToken2.calcLPTokenUnderlying inherits from the IWellFunction interface. However, it doesn't implement all the parameters in the interface. "data" parameter is missing from ProportionalLPToken2.calcLPTokenUnderlying. 

Here are a few potential impacts:

Inability to Calculate Underlying Asset Values

Difficulty in Assessing LP Token Value

Limited Understanding of Pool Composition

Potential Loss of Trading Efficiency

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ProportionalLPToken2.sol#L15C4-L24C6

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/IWellFunction.sol#L52C5-L57C66

## Tools Used
Manual review

## Recommended Mitigation Steps
Include the "data" parameter in the abstract contract. Or remove the parameter from the implementation and interface contract if not needed.


## Assessed type

Error