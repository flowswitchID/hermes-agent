// SPDX-License-Identifier: MIT
pragma solidity 0.8.29;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

contract MythrilTarget2 {
    mapping(address => uint256) public balances;
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    // tx.origin authentication
    function transferOwnership(address newOwner) external {
        require(tx.origin == owner);
        owner = newOwner;
    }
    
    // State change after external call (reentrancy)
    function withdrawLate(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool sent,) = msg.sender.call{value: amount}("");
        require(sent);
        balances[msg.sender] -= amount;
    }
    
    // Unchecked return
    function withdrawToken(address token, uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        IERC20(token).transfer(msg.sender, amount);
    }
    
    // Delegatecall to user address
    function execute(address target, bytes calldata data) external {
        (bool success,) = target.delegatecall(data);
        require(success);
    }
    
    // Timestamp dependence
    function timeLock(uint256 unlockTime) external view returns (bool) {
        return block.timestamp >= unlockTime;
    }
    
    // Multiple external calls in loop
    function distribute(address[] calldata recipients, uint256[] calldata amounts) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool sent,) = recipients[i].call{value: amounts[i]}("");
            require(sent);
        }
    }
    
    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}
