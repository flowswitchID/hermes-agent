// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnWallet {
    address public owner;
    constructor() { owner = msg.sender; }

    function transfer(address payable to, uint256 amount) external {
        require(tx.origin == owner);
        to.transfer(amount);
    }
}
