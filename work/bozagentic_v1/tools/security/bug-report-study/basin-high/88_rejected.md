# #88: Incomplete implementation of interface
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L79C5-L88C6 #L79
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L92C4-L101C2 #L92


# Vulnerability details

## Impact
ConstantProduct2.sol inherits from IBeansTalkWellFunction.sol (an interface). ConstantProduct2.calcReserveAtRatioSwap and ConstantProduct2.calcReserveAtRatioLiquidity both implemented IBeansTalkWellFunction.calcReserveAtRatioSwap and IBeansTalkWellFunction.calcReserveAtRatioSwap.calcReserveAtRatioLiquidit interface. 

However, both ConstantProduct2.calcReserveAtRatioSwap and ConstantProduct2.calcReserveAtRatioLiquidity did not declare the "data" parameter in the interface contract. 

This would lead to compilation error and the ConstantProduct2 contract can't be used.

## Proof of Concept
Here's IBeansTalkWellFunction.calcReserveAtRatioSwap and IBeansTalkWellFunction.calcReserveAtRatioSwap.calcReserveAtRatioLiquidit:

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/IBeanstalkWellFunction.sol#L26C4-L32C1

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/interfaces/IBeanstalkWellFunction.sol#L43C3-L49C2

Here's ConstantProduct2.calcReserveAtRatioSwap and ConstantProduct2.calcReserveAtRatioLiquidity:
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L79C3-L88C6

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/functions/ConstantProduct2.sol#L92

## Tools Used
Manual

## Recommended Mitigation Steps
Include bytes calldata data in the implementation functions.


## Assessed type

Error