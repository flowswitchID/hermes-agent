// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnSend {
    function withdraw(address payable to, uint256 amount) external {
        to.send(amount);
    }
}
