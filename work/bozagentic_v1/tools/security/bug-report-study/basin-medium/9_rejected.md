# #9: Lack of user input validation in many places
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibWellConstructor.sol#L13-L21
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/libraries/LibWellConstructor.sol#L36-L62
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L186-L196


# Vulnerability details

## Impact
There is no or very little validation of functions' parameters

## Proof of Concept
Just see the files in scope, the links above is to highlight some examples

## Tools Used
Manual analysis

## Recommended Mitigation Steps
Check functions parameters (some `require(addr != address(this) or address(0)...`, you know what I mean by that)


## Assessed type

Invalid Validation