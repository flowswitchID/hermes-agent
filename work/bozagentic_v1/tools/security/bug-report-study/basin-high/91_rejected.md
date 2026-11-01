# #91: Non compliance with interface contract
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L49C2-L54C6 #L49
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L58C3-L68C1 #L58


# Vulnerability details

## Impact
ConstantProduct2.calcLpTokenSupply and ConstantProduct2.calcReserve didn't include the "data" parameter in the IWellFunction.calcLpTokenSupply and IWellFunction.calcReserve. 

This would throw an error when any of those two functions is called because the "data" parameter is missing.

## Proof of Concept
Here's IWellFunction.calcLpTokenSupply and IWellFunction.calcReserve:

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/IWellFunction.sol#L36C1-L39C53 

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/IWellFunction.sol#L22C1-L28C1

## Tools Used
Manual

## Recommended Mitigation Steps
Include the "data" parameter in the implementation functions or remove the "data" parameter in the interface contract if it is not needed.


## Assessed type

Error