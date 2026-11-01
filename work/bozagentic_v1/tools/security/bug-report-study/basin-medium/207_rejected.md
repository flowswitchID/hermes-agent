# #207: pump reserves will be corrupted if numberOfReserves become less
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/pumps/MultiFlowPump.sol#L94


# Vulnerability details

## Impact
Pump's reserves will be corrupted.

## Proof of Concept
In MultiFlowPump, we didn't enforce if numberOfReserves has changed from slot.readNumberOfReserves(). If update() is called with less numberOfReserves, the reserves array can be corrupt, leading to unexpected behavior.

For example, we modify test_update_0Seconds to use one reserve instead of two in setUp:

```solidity
        uint256[] memory bbb = new uint256[](1);
        bbb[0] = 2e6;
        mWell.update(address(pump), bbb, new bytes(0));
        mWell.update(address(pump), bbb, new bytes(0));
```

`forge test -vv --match-test test_update_0Seconds`:
```
Running 1 test for test/pumps/Pump.Update.t.sol:PumpUpdateTest
[FAIL. Reason: Index out of bounds] test_update_0Seconds() (gas: 243500)
Logs:
  Error: a ~= b not satisfied [uint]
        Left: 999999
       Right: 2000000
   Max Delta: 1
       Delta: 1000001
```

## Tools Used
Manual Review.

## Recommended Mitigation Steps
Enforce reserves.length == 2 or make sure n == reserves.length after pump initialized.



## Assessed type

Invalid Validation