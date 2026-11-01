# #12: User balance was not updated during minting and burning
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L413
https://github.com/code-423n4/2023-07-basin/blob/c1b72d4e372a6246e0efbd57b47fb4cbb5d77062/src/Well.sol#L548


# Vulnerability details

## Impact
In the function calls to add and remove liquidity, the user balance was not updated. The `addLiquidity()` and `removeLiquidity()` functions are used to add and remove liquidity to the well. Whereby, the `lpTokens` is minted to or burnt from user. This can lead to possible loss of funds or `DOS`as user balances are not `incremented` with the `lpTokens` minted to them or `decremented` when they are burnt.
```solidity
   function _addLiquidity(
        uint256[] memory tokenAmountsIn,
        uint256 minLpAmountOut,
        address recipient,
        bool feeOnTransfer
    ) internal returns (uint256 lpAmountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _updatePumps(_tokens.length);

        if (feeOnTransfer) {
            for (uint256 i; i < _tokens.length; ++i) {
                if (tokenAmountsIn[i] == 0) continue;
                tokenAmountsIn[i] = _safeTransferFromFeeOnTransfer(_tokens[i], msg.sender, tokenAmountsIn[i]);
                reserves[i] = reserves[i] + tokenAmountsIn[i];
            }
        } else {
            for (uint256 i; i < _tokens.length; ++i) {
                if (tokenAmountsIn[i] == 0) continue;
                _tokens[i].safeTransferFrom(msg.sender, address(this), tokenAmountsIn[i]);
                reserves[i] = reserves[i] + tokenAmountsIn[i];
            }
        }

        lpAmountOut = _calcLpTokenSupply(wellFunction(), reserves) - totalSupply();
        if (lpAmountOut < minLpAmountOut) {
            revert SlippageOut(lpAmountOut, minLpAmountOut);
        }

        _mint(recipient, lpAmountOut);
        _setReserves(_tokens, reserves);
        emit AddLiquidity(tokenAmountsIn, lpAmountOut, recipient);
    }
```
## Proof of Concept
User calls `addLiquidity()` inwhich user is minted 2 lpTokens but his balance is not increased by mintamount, this leads to loss of funds by user. Again user then calls `removeliquidity()` passing the number of lptokens to burn,as there is no check that validates the burning, the lptoken is burnt and tokens are transfered to user but still this does not reflect on user balance also leading to loss of funds by the protocol.

## Tools Used
Manual review
## Recommended Mitigation Steps
Increment the user's balance after minting and decrement before burning of `lptokens`.


## Assessed type

Token-Transfer