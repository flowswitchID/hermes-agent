# #49: A malicious user can call boreWell() function with wrong input and skip the If-s
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Aquifer.sol#L40-L71


# Vulnerability details

## Impact
A malicious user can call boreWell() function in `Aquifer.sol` with wrong inputs. This will lead to unknown behave for well reserve.

## Proof of Concept
Alice (the malicious user) calls boreWell() with only implementation input, this will create a well of implementation.clone(), because it will skip the first 2 if-s, and after that will skip all of the next If-s
As for result, it will save the implementation ` wellImplementations[well] = implementation ` and will emit the event.

The other Users will see that and can deposit in this Well reserve and will lose all of their tokens.
## Tools Used
manual 
## Recommended Mitigation Steps
check the inputs 


## Assessed type

Other