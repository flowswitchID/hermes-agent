// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

interface IUACD {
    function totalSupply() external view returns (uint);
    function saleIsActive() external view returns (bool);
    function alreadyMinted(address) external view returns (uint);
    function owner() external view returns (address);
    function baseURI() external view returns (string memory);
    function contractURI() external view returns (string memory);
    function balanceOf(address) external view returns (uint);
    function ownerOf(uint) external view returns (address);
    function getApproved(uint) external view returns (address);
    function isApprovedForAll(address,address) external view returns (bool);
    function mintNFTs(uint) external payable;
    function mintNFTsOwner(uint) external;
    function withdraw() external;
    function activateSales(bool) external;
    function setBaseURI(string memory) external;
    function setContractURI(string memory) external;
}

contract UACDDeep is Test, IERC721Receiver {
    IUACD constant UACD = IUACD(0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5);

    function setUp() public {
        vm.createSelectFork(vm.envString("ETH_RPC_URL"));
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    function test_full_state() public view {
        console.log("=== UACD ON-CHAIN STATE ===");
        console.log("totalSupply:", UACD.totalSupply());
        console.log("saleIsActive:", UACD.saleIsActive());
        console.log("owner:", UACD.owner());
        console.log("contract balance:", address(UACD).balance);
        console.log("baseURI:", UACD.baseURI());

        // Check owner type
        address owner = UACD.owner();
        uint256 codeSize;
        assembly { codeSize := extcodesize(owner) }
        console.log("owner is contract:", codeSize > 0);

        // Check if owner alreadyMinted > 99
        uint256 ownerMinted = UACD.alreadyMinted(owner);
        console.log("owner alreadyMinted:", ownerMinted);
    }

    // ATTACK: Can we call mintNFTsOwner as non-owner?
    function test_unauthorized_owner_mint() public {
        address attacker = makeAddr("attacker");
        vm.startPrank(attacker);
        vm.expectRevert("Ownable: caller is not the owner");
        UACD.mintNFTsOwner(1);
        vm.stopPrank();
    }

    // ATTACK: Can we call withdraw as non-owner?
    function test_unauthorized_withdraw() public {
        address attacker = makeAddr("attacker");
        vm.startPrank(attacker);
        vm.expectRevert("Ownable: caller is not the owner");
        UACD.withdraw();
        vm.stopPrank();
    }

    // ATTACK: Can we call activateSales as non-owner?
    function test_unauthorized_activate() public {
        address attacker = makeAddr("attacker");
        vm.startPrank(attacker);
        vm.expectRevert("Ownable: caller is not the owner");
        UACD.activateSales(true);
        vm.stopPrank();
    }

    // ATTACK: Can we call setBaseURI as non-owner?
    function test_unauthorized_setURI() public {
        address attacker = makeAddr("attacker");
        vm.startPrank(attacker);
        vm.expectRevert("Ownable: caller is not the owner");
        UACD.setBaseURI("ipfs://evil/");
        vm.stopPrank();
    }

    // CHECK: Is sale currently active? Can we mint?
    function test_can_mint_now() public {
        bool active = UACD.saleIsActive();
        console.log("Sale active:", active);
        if (active) {
            address user = makeAddr("minter");
            vm.deal(user, 1 ether);
            vm.startPrank(user);
            UACD.mintNFTs{value: 0.065 ether}(1);
            vm.stopPrank();
            console.log("Mint succeeded! Balance:", UACD.balanceOf(user));
        } else {
            console.log("Sale closed - cannot mint");
        }
    }

    // CHECK: Overpayment on live contract
    function test_overpayment_live() public {
        bool active = UACD.saleIsActive();
        if (!active) { console.log("Sale closed, skip"); return; }
        address user = makeAddr("overpayer");
        vm.deal(user, 1 ether);
        uint256 balBefore = user.balance;
        vm.startPrank(user);
        UACD.mintNFTs{value: 0.5 ether}(1);
        vm.stopPrank();
        uint256 spent = balBefore - user.balance;
        console.log("Paid:", spent);
        console.log("Expected: 0.065 ETH");
        console.log("Overpaid:", spent - 0.065 ether);
        console.log("Contract balance:", address(UACD).balance);
    }

    // CHECK: Owner can drain ALL funds including overpayments
    function test_owner_drain() public {
        uint256 contractBal = address(UACD).balance;
        console.log("Contract balance:", contractBal);
        if (contractBal > 0) {
            address owner = UACD.owner();
            // Simulate owner withdraw
            vm.startPrank(owner);
            uint256 ownerBalBefore = owner.balance;
            UACD.withdraw();
            uint256 received = owner.balance - ownerBalBefore;
            vm.stopPrank();
            console.log("Owner received:", received);
            console.log("Contract balance after:", address(UACD).balance);
        }
    }

    // CHECK: Token ID 0 — does it exist? (off-by-one)
    function test_token_zero() public {
        // _currentId starts at 0, first mint does _currentId++ then _safeMint(to, _currentId)
        // So first token is ID 1, token 0 should NOT exist
        try UACD.ownerOf(0) returns (address owner) {
            console.log("TOKEN 0 EXISTS! Owner:", owner);
            console.log("BUG: Token 0 should not exist");
        } catch {
            console.log("Token 0 does not exist (correct)");
        }
    }

    // CHECK: Can mint 0 amount?
    function test_mint_zero() public {
        bool active = UACD.saleIsActive();
        if (!active) { console.log("Sale closed, skip"); return; }
        address user = makeAddr("zeromint");
        vm.deal(user, 1 ether);
        vm.startPrank(user);
        vm.expectRevert("Amount should not be a zero");
        UACD.mintNFTs{value: 0.065 ether}(0);
        vm.stopPrank();
    }

    // CHECK: Underpayment
    function test_underpayment() public {
        bool active = UACD.saleIsActive();
        if (!active) { console.log("Sale closed, skip"); return; }
        address user = makeAddr("underpayer");
        vm.deal(user, 1 ether);
        vm.startPrank(user);
        vm.expectRevert("Not enough ether to purchase NFT");
        UACD.mintNFTs{value: 0.064 ether}(1); // 0.001 ETH short
        vm.stopPrank();
    }
}
