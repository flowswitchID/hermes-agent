# #87: Invalid comparison of signed and unsigned bytes16 values in _capReserve function
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L205


# Vulnerability details

## Impact
the _capReserve function is used to cap the reserve value to prevent extreme changes. The function applies a cap to both increasing and decreasing reserves. However,so the problem is related to the check for decreasing reserves. The condition if (lastReserve.cmp(reserve) == 1) checks if the last reserve is greater than the current reserve, but it assumes that the comparison is correct for comparing two bytes16 values. 
The comparison logic for bytes16 values vulnerable to subtle issues related to signed/unsigned representation and can lead to unexpected behavior.

## Proof of Concept
the vulnerability can lead to unexpected behavior when comparing bytes16 values, especially the problem lies in the cmp function of the LibBytes16 library, where the comparison between two bytes16 values may not produce the expected results due to the possibility of signed/unsigned representation issues.

## Tools Used
manual review
## Recommended Mitigation Steps
- test the comparison logic to ensure its correctness and consider alternative implementations if necessary.


## Assessed type

Other