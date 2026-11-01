# #287: The `MultiFlowPump.sol/update()` function will neither update nor revert any call made to it by any Well Implementation, hence will fail in storing the correct reserve values.
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor disputed', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L109-L119
https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L205-L215
https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L251-L256
https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L297-L302


# Vulnerability details

## Impact
The `MultiFlowPump` will not be able to update the `lastReserves`, `emaReserves`, `cumulativeReserves`. This will let any attacker to manipulate the value of reserves to any number.

## Proof of Concept
As provided the code of `update` function, the `_getDeltaTimestamp` function is called which gives the difference between the `last timestamp` and `block.timestamp`. Also the variable `alphaN` is dependent on it.
If an attacker calls the `update` function multiple times in a single transaction by using his own deployed smart contract, then as `block.timestamp` remains equal for a transaction, the `lastTimestamp` set by `update` function are all equal and have a value of `block.timestamp`. So, between any two `update` calls of him, the `_getDeltaTimestamp` will give output as `0` .
We can see that `_capReserve` function will not change the reserve for `deltaTimestamp` equals `0`. Which will force the `lastTimestamp` not to change its value.
`alphaN` becomes `1` as it takes `deltaTimestamp` as power of `alpha`, so this also forces the `emaReserves` and `cumulativeReserves` to not change their values.

Due to this, every read only function will output the same value which is stuck during that transaction, even if the funcrtion calculate the fresh value at that time, as calculated by `readInstantaneousReserves`, `_readCumulativeReserves`.

Only the first `update` call of that transaction will change the reserves since at that time the `deltaTimestamp` value will be non-zero, so an attacker can increase the reserves value and then take out all the funds in the next `update` calls of that transaction hence manipulating the `pump`. 

## Tools Used
VSCode

## Recommended Mitigation Steps
This code snippet can be added so that to avoid update call in same transaction.
```solidity
        if (deltaTimestamp == bytes16(0)) {
            revert NoTimePassed();
        }
```



## Assessed type

Oracle