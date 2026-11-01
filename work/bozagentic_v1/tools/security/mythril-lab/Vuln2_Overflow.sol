// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnOverflow {
    mapping(address => uint256) public balances;

    function transfer(address to, uint256 amount) external {
        unchecked {
            balances[msg.sender] -= amount;
        }
        balances[to] += amount;
    }
}
