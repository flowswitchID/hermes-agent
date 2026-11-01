// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// Minimal ERC20 mock for symbolic testing
contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function mint(address to, uint256 amt) external {
        balanceOf[to] += amt;
        totalSupply += amt;
    }
    function approve(address spender, uint256 amt) external returns (bool) {
        allowance[msg.sender][spender] = amt;
        return true;
    }
    function transfer(address to, uint256 amt) external returns (bool) {
        require(balanceOf[msg.sender] >= amt);
        balanceOf[msg.sender] -= amt;
        balanceOf[to] += amt;
        return true;
    }
    function transferFrom(address from, address to, uint256 amt) external returns (bool) {
        require(balanceOf[from] >= amt);
        require(allowance[from][msg.sender] >= amt);
        allowance[from][msg.sender] -= amt;
        balanceOf[from] -= amt;
        balanceOf[to] += amt;
        return true;
    }
}

// Minimal drainer for symbolic testing
contract SimpleDrainer {
    address public owner;
    constructor() { owner = msg.sender; }

    function drain(address token, address victim, address to) external returns (uint256) {
        require(msg.sender == owner);
        uint256 allow = MockERC20(token).allowance(victim, address(this));
        uint256 bal = MockERC20(token).balanceOf(victim);
        uint256 amt = allow < bal ? allow : bal;
        if (amt > 0) MockERC20(token).transferFrom(victim, to, amt);
        return amt;
    }
}

contract HalmosDrainerTest is Test {
    SimpleDrainer drainer;
    MockERC20 token;

    function setUp() public {
        drainer = new SimpleDrainer();
        token = new MockERC20();
    }

    // SYMBOLIC: for ANY mint/approve amounts, drain never exceeds allowance
    function check_drain_bounded(uint256 mintAmt, uint256 approveAmt) public {
        address victim = address(0x1234);
        address owner = drainer.owner();

        token.mint(victim, mintAmt);
        vm.prank(victim);
        token.approve(address(drainer), approveAmt);

        vm.prank(owner);
        uint256 drained = drainer.drain(address(token), victim, owner);

        // PROPERTY: drained <= min(mintAmt, approveAmt)
        uint256 maxPossible = mintAmt < approveAmt ? mintAmt : approveAmt;
        assert(drained <= maxPossible);

        // PROPERTY: victim keeps at least (mintAmt - approveAmt) if approve < mint
        if (approveAmt < mintAmt) {
            assert(token.balanceOf(victim) >= mintAmt - approveAmt);
        }
    }

    // SYMBOLIC: non-owner drain always reverts (no expectRevert — halmos doesn't support it)
    function check_access_control(address caller, address victim) public {
        vm.assume(caller != drainer.owner());
        // If non-owner calls drain, it MUST revert
        // Halmos will explore: does any path exist where non-owner succeeds?
        vm.prank(caller);
        drainer.drain(address(token), victim, caller);
        // If we reach here, access control is BROKEN
        assert(false);
    }

    // SYMBOLIC: drain with zero allowance = zero drained
    function check_zero_allowance(uint256 mintAmt) public {
        address victim = address(0x5678);
        token.mint(victim, mintAmt);
        // NO approve

        vm.prank(drainer.owner());
        uint256 drained = drainer.drain(address(token), victim, drainer.owner());

        assert(drained == 0);
        assert(token.balanceOf(victim) == mintAmt);
    }

    // SYMBOLIC: totalSupply conservation
    function check_supply_conservation(uint256 amt) public {
        address a = address(0xA);
        address b = address(0xB);
        token.mint(a, amt);

        uint256 supplyBefore = token.totalSupply();
        vm.prank(a);
        token.transfer(b, amt / 2);

        // PROPERTY: transfer doesn't change totalSupply
        assert(token.totalSupply() == supplyBefore);
        assert(token.balanceOf(a) + token.balanceOf(b) == amt);
    }
}
