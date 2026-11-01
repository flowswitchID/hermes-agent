// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title ComplexVault — multiple vuln classes for Mythril deep exploration
contract ComplexVault {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    uint256 public totalDeposits;
    address public owner;
    bool public paused;
    
    // Vulnerability 1: Integer issue in fee calc
    uint256 public feeBps = 30; // 0.3%
    
    // Vulnerability 2: State ordering
    struct Lock {
        uint256 amount;
        uint256 unlockTime;
        bool claimed;
    }
    mapping(address => Lock[]) public locks;
    
    // Vulnerability 3: External call patterns
    address public feeRecipient;
    
    event Deposited(address indexed user, uint256 amount, uint256 fee);
    event Withdrawn(address indexed user, uint256 amount);
    event Locked(address indexed user, uint256 amount, uint256 until);
    
    constructor() {
        owner = msg.sender;
        feeRecipient = msg.sender;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }
    
    modifier whenNotPaused() {
        require(!paused, "paused");
        _;
    }
    
    function deposit() external payable whenNotPaused {
        require(msg.value > 0, "zero");
        
        // Fee calculation — potential rounding issue
        uint256 fee = (msg.value * feeBps) / 10000;
        uint256 netAmount = msg.value - fee;
        
        balances[msg.sender] += netAmount;
        totalDeposits += netAmount;
        
        // External call for fee — check ordering
        if (fee > 0) {
            (bool sent,) = feeRecipient.call{value: fee}("");
            require(sent, "fee failed");
        }
        
        emit Deposited(msg.sender, netAmount, fee);
    }
    
    function withdraw(uint256 amount) external whenNotPaused {
        require(amount > 0, "zero");
        require(balances[msg.sender] >= amount, "insufficient");
        
        // State update BEFORE transfer (correct)
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        
        (bool sent,) = msg.sender.call{value: amount}("");
        require(sent, "transfer failed");
        
        emit Withdrawn(msg.sender, amount);
    }
    
    // Vulnerability: lock with loop — Mythril should explore bounds
    function createLock(uint256 amount, uint256 duration) external whenNotPaused {
        require(amount > 0 && duration > 0, "zero");
        require(balances[msg.sender] >= amount, "insufficient");
        
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        
        locks[msg.sender].push(Lock({
            amount: amount,
            unlockTime: block.timestamp + duration,
            claimed: false
        }));
        
        emit Locked(msg.sender, amount, block.timestamp + duration);
    }
    
    // Vulnerability: claim with loop iteration
    function claimLocks() external {
        Lock[] storage userLocks = locks[msg.sender];
        uint256 totalClaimable = 0;
        
        for (uint256 i = 0; i < userLocks.length; i++) {
            if (userLocks[i].unlockTime <= block.timestamp && !userLocks[i].claimed) {
                userLocks[i].claimed = true;
                totalClaimable += userLocks[i].amount;
            }
        }
        
        require(totalClaimable > 0, "nothing to claim");
        balances[msg.sender] += totalClaimable;
        totalDeposits += totalClaimable;
    }
    
    // Vulnerability: allowance race condition pattern
    function approve(address spender, uint256 amount) external {
        allowances[msg.sender][spender] = amount;
    }
    
    function transferFrom(address from, address to, uint256 amount) external {
        require(allowances[from][msg.sender] >= amount, "not allowed");
        require(balances[from] >= amount, "insufficient");
        
        allowances[from][msg.sender] -= amount;
        balances[from] -= amount;
        balances[to] += amount;
    }
    
    // Vulnerability: owner can change fee to extreme values
    function setFee(uint256 newFee) external onlyOwner {
        feeBps = newFee; // No upper bound check!
    }
    
    function setFeeRecipient(address newRecipient) external onlyOwner {
        feeRecipient = newRecipient;
    }
    
    function pause() external onlyOwner {
        paused = !paused;
    }
    
    // Emergency withdraw — potential access control issue
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(owner, amount);
    }
    
    receive() external payable {
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
    }
}
