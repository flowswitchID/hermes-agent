// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract AuditTarget {
    address public owner;
    uint256 public constant MAX_FEE = 1000;
    uint256 public fee;
    mapping(address => uint256) public balances;
    
    // Issue: missing event for critical change
    constructor() {
        owner = msg.sender;
        fee = 100;
    }
    
    // Issue: tx.origin
    function adminAction() external {
        require(tx.origin == owner, "not owner");
        fee = 0;
    }
    
    // Issue: unchecked return
    function withdraw(address token, uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        IERC20(token).transfer(msg.sender, amount);
    }
    
    // Issue: block.timestamp
    function timeBased() external view returns (bool) {
        return block.timestamp > 1700000000;
    }
    
    // Issue: deprecated OZ functions
    function unsafeERC20() external {
        IERC20(address(0)).approve(address(1), type(uint256).max);
    }
    
    // Issue: division before multiplication
    function badMath(uint256 a, uint256 b, uint256 c) external pure returns (uint256) {
        return (a / b) * c; // precision loss
    }
    
    // Issue: missing zero address check
    function setOwner(address newOwner) external {
        require(msg.sender == owner);
        owner = newOwner; // no zero check
    }
    
    // Issue: boolean comparison
    function check(bool flag) external pure returns (bool) {
        if (flag == true) return true;
        return false;
    }
    
    // Issue: unused named return
    function unusedReturn(uint256 x) external pure returns (uint256 result) {
        return x * 2; // 'result' never used
    }
    
    // Issue: assembly usage
    function asmBlock() external view returns (uint256 val) {
        assembly {
            val := sload(0)
        }
    }
    
    // Issue: TODO comment
    // TODO: implement proper access control
    
    receive() external payable {
        balances[msg.sender] += msg.value;
    }
}
