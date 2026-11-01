# #177: Pump is not updated in `shift` function
Labels: ['bug', '3 (High Risk)', 'partial-25', 'upgraded by judge', 'duplicate-136']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377


# Vulnerability details

## Impact
According to comments in [`Well` contract](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L641-L644C8), `_updatePumps` function "Fetches the current token reserves of the Well and updates the Pumps. Typically called before an operation that modifies the Well's reserves."

In functions like swap, add/remove liquidity `_updatePumps` is called, but in `shift` function pumps are not updated even though the function works like a swap function, where reserves are changed.

As a result - pumps are not updated when they are expected to.

## Proof of Concept
Function [`Well._updatePumps`](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L645-L670)
```solidity
    function _updatePumps(uint256 _numberOfTokens) internal returns (uint256[] memory reserves) {
        reserves = _getReserves(_numberOfTokens);

        if (numberOfPumps() == 0) {
            return reserves;
        }

        // gas optimization: avoid looping if there is only one pump
        if (numberOfPumps() == 1) {
            Call memory _pump = firstPump();
            // Don't revert if the update call fails.
            try IPump(_pump.target).update(reserves, _pump.data) {}
            catch {
                // ignore reversion. If an external shutoff mechanism is added to a Pump, it could be called here.
            }
        } else {
            Call[] memory _pumps = pumps();
            for (uint256 i; i < _pumps.length; ++i) {
                // Don't revert if the update call fails.
                try IPump(_pumps[i].target).update(reserves, _pumps[i].data) {}
                catch {
                    // ignore reversion. If an external shutoff mechanism is added to a Pump, it could be called here.
                }
            }
        }
    }
```

is called in:
- [addLiquidity](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L420)
- [removeLiquidity](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L467)
- [swapFrom](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L223)
- [swapTo](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L273)

This is correct according to the comments in the contract.

However, in [`shift`](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377) (which functions like a `swapFrom` and `swapTo` function) `_updatePumps` function is not called even though the reserves are updated

## Tools Used
Manual Review

## Recommended Mitigation Steps
Add `_updatePumps` function to `shift` function.
```solidity
    function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        _updatePumps(_tokens.length);
        uint256[] memory reserves = new uint256[](_tokens.length);

        // Use the balances of the pool instead of the stored reserves.
        // If there is a change in token balances relative to the currently
        // stored reserves, the extra tokens can be shifted into `tokenOut`.
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(address(this));
        }
        uint256 j = _getJ(_tokens, tokenOut);
        amountOut = reserves[j] - _calcReserve(wellFunction(), reserves, j, totalSupply());

        if (amountOut >= minAmountOut) {
            tokenOut.safeTransfer(recipient, amountOut);
            reserves[j] -= amountOut;
            _setReserves(_tokens, reserves);
            emit Shift(reserves, tokenOut, amountOut, recipient);
        } else {
            revert SlippageOut(amountOut, minAmountOut);
        }
    }
```


## Assessed type

Context