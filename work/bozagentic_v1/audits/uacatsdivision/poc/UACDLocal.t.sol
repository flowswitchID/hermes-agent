// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract UACDLocal is Test, IERC721Receiver {
    UACatsDivision nft;
    address owner = address(this);
    address user1 = address(0x1111);
    address user2 = address(0x2222);

    function setUp() public {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
        vm.deal(user1, 100 ether);
        vm.deal(user2, 100 ether);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return this.onERC721Received.selector;
    }

    // BUG 1: Overpayment not refunded (CONFIRMED)
    function test_overpayment_not_refunded() public {
        vm.startPrank(user1);
        uint256 balBefore = user1.balance;
        nft.mintNFTs{value: 1 ether}(1);
        uint256 spent = balBefore - user1.balance;
        vm.stopPrank();
        assertEq(spent, 1 ether);
        assertEq(address(nft).balance, 1 ether);
        console.log("OVERPAYMENT: paid 1 ETH for 0.065 ETH NFT");
        console.log("Lost:", spent - 0.065 ether);
    }

    // BUG 1b: No refund mechanism exists
    function test_no_refund() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 10 ether}(5);
        vm.stopPrank();
        assertEq(address(nft).balance, 10 ether);
        console.log("NO REFUND: 9.675 ETH stuck, only owner can withdraw");
    }

    // BUG 1c: Owner withdraw takes overpayment
    function test_withdraw_takes_overpayment() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 5 ether}(1);
        vm.stopPrank();
        uint256 ownerBal = owner.balance;
        nft.withdraw();
        assertEq(owner.balance - ownerBal, 5 ether);
        console.log("OWNER takes ALL including overpayment");
    }

    // CORRECTED: Owner mint IS tracked in _alreadyMinted
    function test_owner_mint_tracked() public {
        nft.mintNFTsOwner(50);
        assertEq(nft.alreadyMinted(owner), 50, "IS tracked");
        assertEq(nft.balanceOf(owner), 50);
    }

    // BUG 2: Owner bypasses MAX_PER_ACCOUNT check
    function test_owner_bypass_limit() public {
        nft.mintNFTsOwner(100); // > MAX_PER_ACCOUNT (99)
        assertEq(nft.balanceOf(owner), 100);
        assertEq(nft.alreadyMinted(owner), 100);
        console.log("OWNER BYPASS: minted 100 > MAX_PER_ACCOUNT(99)");
        // But this is BY DESIGN for team mint
    }

    // BUG 3: Owner can mint + public mint = exceed 99
    function test_owner_exceed_99() public {
        nft.mintNFTsOwner(50);
        // alreadyMinted = 50, so public mint limited to 49
        nft.mintNFTs{value: 0.065 ether * 49}(49);
        assertEq(nft.balanceOf(owner), 99);
        // Can't mint more via public
        vm.expectRevert("You have exceeded max NFT count for your account");
        nft.mintNFTs{value: 0.065 ether}(1);
        // But CAN mint more via owner mint
        nft.mintNFTsOwner(1);
        assertEq(nft.balanceOf(owner), 100);
        console.log("Owner: 50 owner + 49 public + 1 owner = 100");
    }

    function test_exact_payment() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        assertEq(nft.balanceOf(user1), 1);
        assertEq(address(nft).balance, 0.065 ether);
    }

    function test_max_per_account() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether * 99}(99);
        vm.expectRevert("You have exceeded max NFT count for your account");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
    }

    function test_sale_closed() public {
        nft.activateSales(false);
        vm.startPrank(user1);
        vm.expectRevert("Sale is closed");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
    }

    function test_max_supply() public {
        nft.mintNFTsOwner(9999);
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        assertEq(nft.totalSupply(), 10000);
        vm.startPrank(user2);
        vm.expectRevert("Not enough NFT left to mint");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
    }

    function test_safeMint_reentrancy() public {
        AttackerContract attacker = new AttackerContract(address(nft));
        vm.deal(address(attacker), 10 ether);
        attacker.attack{value: 0.065 ether}();
        // nonReentrant blocks re-entry
        assertEq(nft.balanceOf(address(attacker)), 1, "Only 1 minted");
        console.log("Reentrancy BLOCKED by nonReentrant");
    }

    // FUZZ: overpayment (fixed)
    function testFuzz_overpayment(uint8 amount, uint256 extra) public {
        vm.assume(amount > 0 && amount <= 99);
        vm.assume(extra <= 10 ether);
        uint256 payAmount = uint256(amount) * 0.065 ether + extra;
        vm.deal(user1, payAmount);
        vm.startPrank(user1);
        nft.mintNFTs{value: payAmount}(amount);
        vm.stopPrank();
        assertEq(address(nft).balance, payAmount, "Contract keeps ALL");
        // Overpayment = extra, NOT refunded
    }

    receive() external payable {}
}

contract AttackerContract is IERC721Receiver {
    UACatsDivision nft;
    bool attacking;

    constructor(address _nft) { nft = UACatsDivision(_nft); }

    function attack() external payable {
        attacking = true;
        nft.mintNFTs{value: msg.value}(1);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external returns (bytes4) {
        if (attacking) {
            attacking = false;
            try nft.mintNFTs{value: 0.065 ether}(1) {} catch {}
        }
        return IERC721Receiver.onERC721Received.selector;
    }

    receive() external payable {}
}
