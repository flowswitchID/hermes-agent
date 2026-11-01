# #228: The existence of Pump may hinder large swaps or swaps from a low liquidity pool
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L656-L659
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/pumps/MultiFlowPump.sol#L72-L140


# Vulnerability details

## Impact

Large swaps or swaps with low liquidity value may not work properly.

## Proof of Concept

According to the [whitepaper](https://basin.exchange/multi-flow-pump.pdf), the purpose of the pump is to be a multi-block MEV manipulation resistant to large changes in liquidity value. 

Since the Well can be created permissionlessly by anyone through boreWell() following a proper implementation, there can exist many AMMs with low liquidity value. If a user intends to use those low liquidity value wells, the value of tokenA and tokenB might change drastically after a swap. Due to the existence of the pump, if the change is too large, the swap may not work, rendering the low liquidity wells ineffective as an AMM.

Similarly, a large swap can affect the value of either tokens and this swap will be negated by the pump.

When a swap occurs, `_updatePumps()` is called.

```
    function swapTo(
        IERC20 fromToken,
        IERC20 toToken,
        uint256 maxAmountIn,
        uint256 amountOut,
        address recipient,
        uint256 deadline
    ) external nonReentrant expire(deadline) returns (uint256 amountIn) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);
```

`_updatePumps()` checks for the existence of pumps and calls `update()` , which does all the time-weight multi-block resistant calculations.

```
    function update(uint256[] calldata reserves, bytes calldata) external {
        uint256 numberOfReserves = reserves.length;
        PumpState memory pumpState;


        // All reserves are stored starting at the msg.sender address slot in storage.
        bytes32 slot = _getSlotForAddress(msg.sender);


        // Read: Last Timestamp & Last Reserves
        (, pumpState.lastTimestamp, pumpState.lastReserves) = slot.readLastReserves();


        // If the last timestamp is 0, then the pump has never been used before.
        if (pumpState.lastTimestamp == 0) {
            for (uint256 i; i < numberOfReserves; ++i) {
                // If a reserve is 0, then the pump cannot be initialized.
                if (reserves[i] == 0) return;
            }
            _init(slot, uint40(block.timestamp), reserves);
            return;
        }


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


        bytes16 alphaN;
        bytes16 deltaTimestampBytes;
        bytes16 blocksPassed;
        // Isolate in brackets to prevent stack too deep errors
        {
            uint256 deltaTimestamp = _getDeltaTimestamp(pumpState.lastTimestamp);
            alphaN = ALPHA.powu(deltaTimestamp);
            deltaTimestampBytes = deltaTimestamp.fromUInt();
            // Relies on the assumption that a block can only occur every `BLOCK_TIME` seconds.
            blocksPassed = (deltaTimestamp / BLOCK_TIME).fromUInt();
        }


        for (uint256 i; i < numberOfReserves; ++i) {
            // Use a minimum of 1 for reserve. Geometric means will be set to 0 if a reserve is 0.
            pumpState.lastReserves[i] = _capReserve(
                pumpState.lastReserves[i], (reserves[i] > 0 ? reserves[i] : 1).fromUIntToLog2(), blocksPassed
            );
            pumpState.emaReserves[i] =
                pumpState.lastReserves[i].mul((ABDKMathQuad.ONE.sub(alphaN))).add(pumpState.emaReserves[i].mul(alphaN));
            pumpState.cumulativeReserves[i] =
                pumpState.cumulativeReserves[i].add(pumpState.lastReserves[i].mul(deltaTimestampBytes));
        }


        // Write: Cumulative & EMA Reserves
        // Order matters: work backwards to avoid using a new memory var to count up
        slot.storeBytes16(pumpState.cumulativeReserves);
        assembly {
            slot := sub(slot, numSlots)
        }
        slot.storeBytes16(pumpState.emaReserves);
        assembly {
            slot := sub(slot, numSlots)
        }


        // Write: Last Timestamp & Last Reserves
        slot.storeLastReserves(uint40(block.timestamp), pumpState.lastReserves);
    }
```

For now, there is no reversion because an external shutoff mechanism is not yet implemented.

```
            try IPump(_pump.target).update(reserves, _pump.data) {}
            catch {
                // ignore reversion. If an external shutoff mechanism is added to a Pump, it could be called here.
            }
```

However, if, as the video documentation states, the cutoff is a 50% increase/decrease in either tokenA or tokenB, then the swap should be reverted. In that case, a low liquidity pool or a large swap cannot happen in the Wells because the pump does not consider that such drastic changes can happen without manipulation.

## Tools Used

VSCode

## Recommended Mitigation Steps

Not really sure about the ideal way to fix this situation, but one recommendation is to check the amountIn() before every swap. If the amountIn() is extremely large or a large percentage compared to the total value, then the pump can be manually switched off. 


## Assessed type

Context