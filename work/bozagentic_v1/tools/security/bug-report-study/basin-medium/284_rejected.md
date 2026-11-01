# #284: bad actore can increase gas usage in swapfrom function 
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Well.sol#L636-L637


# Vulnerability details

## Impact
bad actor can increase gas in swapfrom function because everytime calling swapfrom function it store new unit and everytime runs the loop for length of it 
## Proof of Concept
the swapfrom function includes 

```soldity
    function _setReserves(IERC20[] memory _tokens, uint256[] memory reserves) internal {
        for (uint256 i; i < reserves.length; ++i) {
            if (reserves[i] > _tokens[i].balanceOf(address(this))) revert InvalidReserves();
        }
        LibBytes.storeUint128(RESERVES_STORAGE_SLOT, reserves);
    }

```

which is not recommended logic because every time people wants to swap function calls the setreservee and it actually runs loop and go through the length of reserves and bad actor can abuse it and increase gas

## Tools Used
manually / vscode
## Recommended Mitigation Steps
- consider making a max trade for the account in day or sth like that



## Assessed type

DoS