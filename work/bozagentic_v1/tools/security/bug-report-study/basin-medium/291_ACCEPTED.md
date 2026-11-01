# #291: `Well.skim()` TRANSACTION CAN BE FRONT RUN BY `Well.sync()` TRANSACTION THUS MAKING THE `Well.skim()` CALL INEFFECTIVE 
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'primary issue', 'unsatisfactory']
Accepted: True

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613
https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L590-L598


# Vulnerability details

## Impact
 The `Well.skim()` external function is used to transfer the excess tokens held by the well to teh `recipient`. This is done by calculating the differnce between the contract balance and the reserves for each of the tokens as shown below:

            skimAmounts[i] = _tokens[i].balanceOf(address(this)) - reserves[i];

But the `skim()` function can be front run by calling the `Well.sync()` function. This will make the reserves eqaul the current contract balance of each of the tokens as shown below:

            reserves[i] = _tokens[i].balanceOf(address(this));

Hence this will make the `Well.skim()` transaction useless, since now there is no difference between contract balance and the reserve balance for each of the tokens.

## Proof of Concept

```solidity
    function skim(address recipient) external nonReentrant returns (uint256[] memory skimAmounts) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = _getReserves(_tokens.length);
        skimAmounts = new uint256[](_tokens.length);
        for (uint256 i; i < _tokens.length; ++i) {
            skimAmounts[i] = _tokens[i].balanceOf(address(this)) - reserves[i];
            if (skimAmounts[i] > 0) {
                _tokens[i].safeTransfer(recipient, skimAmounts[i]);
            }
        }
    }
```

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613

```solidity
    function sync() external nonReentrant {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(address(this));
        }
        _setReserves(_tokens, reserves);
        emit Sync(reserves);
    }
```

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L590-L598

## Tools Used
Manual Review and VSCode

## Recommended Mitigation Steps

There should be access control on who can call the `Well.sync()` and `Well.skim()` functions.  
And `pause` functionality or `Timelock` functionality can be implemented with the `Well.sync()`, so that admin can `pause` or `timelock` this function before calling the `Well.skim()` function. 


## Assessed type

Access Control