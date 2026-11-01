# #15: Anyone can update reserves with arbitrary amounts
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/pumps/MultiFlowPump.sol#L72


# Vulnerability details

## Impact
Anyone can call the `update`function inside `MultiFlowPump.sol` with arbitrary `reserves` parameter, thus modifying state variables in slots through low level storage functions.

## Proof of Concept
There no check to ensure the caller is a trusted one

```
function update(uint256[] calldata reserves, bytes calldata) external {
                                                            ^-------------- NO MOD NOR REQUIRES BELOW
```

## Tools Used
Manual analysis

## Recommended Mitigation Steps
Ensure the caller is a trusted one or validate correctly the `reserves` parameters


## Assessed type

Access Control