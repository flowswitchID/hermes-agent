# #99: byteReserves will be different in SMA compare to EMA & Resistant Last Values
Labels: ['bug', '3 (High Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L92-L102
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L157-L166


# Vulnerability details

## Summary

1 Multi-Block MEV Manipulation Resistant Last Values
2 Multi-Block MEV Manipulation Resistant Instantaneous Values
3.Multi-Block MEV-Resistant Time-Weighted Average Values
use same byte Reserves.
But in init function in MultiFlowPump we just write Last Reserves for Resistant Last Values and EMA(not SMA)
so slot for SMA will be zero at first.
## Proof of Concept
when ever we want to update in MultiFlowPump contract in line 92
```
        // Read: Cumulative & EMA Reserves
        // Start at the slot after `pumpState.lastReserves`
        uint256 numSlots = _getSlotsOffset(numberOfReserves);
        assembly {
            slot := add(slot, numSlots)
        }
        pumpState.emaReserves = slot.readBytes16(numberOfReserves);
        assembly {
            slot := add(slot, numSlots)
        }
        pumpState.cumulativeReserves = slot.readBytes16(numberOfReserves);
```
We read Cumulative & EMA Reserves, but at init function we just write EMA Reserves.
```
        // Write: Last Timestamp & Last Reserves
        slot.storeLastReserves(lastTimestamp, byteReserves);


        // Write: EMA Reserves
        // Start at the slot after `byteReserves`
        uint256 numSlots = _getSlotsOffset(byteReserves.length);
        assembly {
            slot := add(slot, numSlots)
        }
        slot.storeBytes16(byteReserves); // EMA Reserves
```

## Impact

Impact:0 values in SMA slot at init function(will be different from EMA)

## Tools Used

manual

## Recommended Mitigation Steps
in init function write slot for SMA as well
```
+        assembly {
+            slot := add(slot, numSlots)
+        }
+        slot.storeBytes16(byteReserves); 
```



## Assessed type

Other