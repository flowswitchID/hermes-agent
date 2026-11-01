# #102: In Well.sol, Calls inside loops that may address DoS
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L423-L427
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L429-L433
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L473-L477
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L557-L558
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L607-L611


# Vulnerability details

## Impact
Calls to external contracts inside a loop are dangerous because it could lead to DoS if one of the calls reverts or execution runs out of gas. Such issue also introduces chance of problems with the gas limits. 

**Per SWC-113:**
External calls can fail accidentally or deliberately, which can cause a DoS condition in the contract. To minimize the damage caused by such failures, it is better to isolate each external call into its own transaction that can be initiated by the recipient of the call.

Reference link- https://swcregistry.io/docs/SWC-113

## Proof of Concept
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L423-L427

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L429-L433

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L473-L477

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L557-L558

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L607-L611

## References

1) Similar Medium severity issue found in Cudos audit:  [Reference link](https://github.com/code-423n4/2022-05-cudos-findings/issues/126) 

2) SWC-113(DoS with Failed Call): [Reference link](https://swcregistry.io/docs/SWC-113)

3) Consensys best practices: [Reference link](https://consensys.github.io/smart-contract-best-practices/recommendations/#favor-pull-over-push-for-external-calls)


## Tools Used
Manual review

## Recommended Mitigation Steps
1) Avoid combining multiple calls in a single transaction, especially when calls are executed as part of a loop
2) Always assume that external calls can fail
3) Implement the contract logic to handle failed calls



## Assessed type

DoS