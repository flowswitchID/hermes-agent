# #97: miss check for _maxPercentIncrease to not be to high
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory', 'edited-by-warden']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L54


# Vulnerability details

## Summary

As in Multi Flow: Multi-block MEV Resistant Pump For Current Values mentioned in Resistant Last Values
there is maximum increase permitted of a value per block (γ+), maximum decrease permitted
of a value per block (γ−), it should be an upper bound for (γ+) to not allow high increases.

## Impact

Allowed huge increases per block.

## Tools Used

manual

## Recommended Mitigation Steps
for an example, add upper bound of ABDKMathQuad.ONE
```
     constructor(bytes16 _maxPercentIncrease, bytes16 _maxPercentDecrease, uint256 _blockTime, bytes16 _alpha) {
+        if (_maxPercentIncrease > ABDKMathQuad.ONE) {
+            revert();}
```





## Assessed type

Other