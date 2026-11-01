# #96: Evaluation of Condition in storeUint128 Function
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/libraries/LibBytes.sol#L62


# Vulnerability details

## Impact
the storeUint128 function, when checking if there are an odd number of reserves, the condition reserves.
length & 1 == 1 is used, this condition may not work as intended, the & operator has higher precedence than 
the == operator, without proper parentheses to group the expressions correctly, the condition may be evaluated incorrectly. The current expression reserves.length & 1 == 1 can be interpreted as (reserves.length & 1) == 1, which checks if the result of the bitwise AND operation is equal to 1.

## Proof of Concept
. If the condition reserves.length & 1 == 1 is not evaluated correctly, it can result in incorrect slot creation when there is an odd number of reserves, and  if the condition is evaluated incorrectly, it may lead to an improper storage slot allocation for the last reserve. This can potentially cause issues such as data corruption, storage collisions, or unexpected behavior when reading or updating data.

## Tools Used
manual review
## Recommended Mitigation Steps
update the condition to (reserves.length & 1) == 1 to ensure proper evaluation and avoid any potential issues


## Assessed type

Other