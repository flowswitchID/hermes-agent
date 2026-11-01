# #276: the swapFrom() function allows the Fee On Transfer tokens and _setReserves doesn't revert 
Labels: ['bug', '3 (High Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L632-L638


# Vulnerability details

## Impact
the protocol supports the `fee on transfer` tokens and has implemented a special capable function for it and wants to not allow and revert the fee on transfer tokens in normal SwapFrom function as it says in 

comments of swapfrom function 
`@dev MUST revert if a fee on transfer token is used. The requisite checkis performed in {_setReserves}.
`

so with that information, the `_setReserves` must be able to revert in fee on transfer tokens but it actually doesn't do that.

now imagine the normal swap from function accepts fee on the transfer function and it will create dangerous unwanted results.

## Proof of Concept
here in comments of swapfrom it says 

```solidity 
  /**
     * @dev MUST revert if a fee on transfer token is used. The requisite check
     * is performed in {_setReserves}.
     */
    function swapFrom(
```
but let's look at the 
_setReserves function
```solidity

  function _setReserves(IERC20[] memory _tokens, uint256[] memory reserves) internal {
        for (uint256 i; i < reserves.length; ++i) {
            if (reserves[i] > _tokens[i].balanceOf(address(this))) revert InvalidReserves();
        }
        LibBytes.storeUint128(RESERVES_STORAGE_SLOT, reserves);
    }
```

it actually doesn't revert when the fee on the transfer token is used 


## Tools Used

## Recommended Mitigation Steps
there are several ways to mitigate that 

- consider implementing simple whitelist logic
- add extra checks that checks the transferred amount balance precisely like in _safeTransferFromFeeOnTransfer logic 
```solidity
  uint256 balanceBefore = token.balanceOf(address(this));
        token.safeTransferFrom(from, address(this), amount);
        amountTransferred = token.balanceOf(address(this)) - balanceBefore;
```


## Assessed type

Token-Transfer