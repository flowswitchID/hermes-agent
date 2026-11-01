# #178: Absence of Function calcReserve(...) at src/interfaces/IBeanstalkWellFunction.sol
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L695-L702


# Vulnerability details

## Impact
Absence of Function calcReserve(...) at src/interfaces/IBeanstalkWellFunction.sol will affect the implementation of the function, the implementation is done in src/functions/ConstantProduct2.sol but the implementation cannot be accessed at src/interfaces/IWellFunction.sol due to it absence in IBeanstalkWellFunction contract. Therefore the function is of no use in the src/Well.sol contract

## Proof of Concept
Interface function requires implementation but cannot be accessed by Well contract from IWellFunction interface due to absence at IBeanstalkWellFunction interface

## Tools Used
Solidity, Foundry

## Recommended Mitigation Steps
Function calcReserve(...) should be present at IBeanstalkWellFunction contract of src/interfaces/IBeanstalkWellFunction.sol





## Assessed type

Access Control