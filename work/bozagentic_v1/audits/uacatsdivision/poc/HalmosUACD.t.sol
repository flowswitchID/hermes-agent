// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract HalmosUACD is Test, IERC721Receiver {
    UACatsDivision nft;

    function setUp() public {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    // PROPERTY: totalSupply always <= MAX_SUPPLY
    function check_supply_bounded(uint8 amount) public {
        vm.assume(amount > 0 && amount <= 99);
        uint256 supply = nft.totalSupply();
        if (supply + amount > 10000) return;
        address user = address(0xBEEF);
        vm.deal(user, amount * 0.065 ether);
        vm.startPrank(user);
        nft.mintNFTs{value: amount * 0.065 ether}(amount);
        vm.stopPrank();
        assertLe(nft.totalSupply(), 10000);
    }

    // PROPERTY: balanceOf(user) == amount minted
    function check_balance_correct(uint8 amount) public {
        vm.assume(amount > 0 && amount <= 99);
        address user = address(0xBEEF);
        vm.deal(user, amount * 0.065 ether);
        vm.startPrank(user);
        nft.mintNFTs{value: amount * 0.065 ether}(amount);
        vm.stopPrank();
        assertEq(nft.balanceOf(user), amount);
    }

    // PROPERTY: alreadyMinted tracks correctly
    function check_already_minted(uint8 amount) public {
        vm.assume(amount > 0 && amount <= 99);
        address user = address(0xBEEF);
        vm.deal(user, amount * 0.065 ether);
        vm.startPrank(user);
        nft.mintNFTs{value: amount * 0.065 ether}(amount);
        vm.stopPrank();
        assertEq(nft.alreadyMinted(user), amount);
    }

    // PROPERTY: contract balance >= totalSupply * PRICE (before withdraw)
    function check_balance_solvency(uint8 amount) public {
        vm.assume(amount > 0 && amount <= 99);
        address user = address(0xBEEF);
        vm.deal(user, amount * 0.065 ether);
        vm.startPrank(user);
        nft.mintNFTs{value: amount * 0.065 ether}(amount);
        vm.stopPrank();
        assertGe(address(nft).balance, nft.totalSupply() * 0.065 ether);
    }

    // PROPERTY: overpayment stays in contract (no refund)
    function check_overpayment_kept(uint8 amount, uint256 extra) public {
        vm.assume(amount > 0 && amount <= 10);
        vm.assume(extra > 0 && extra <= 1 ether);
        address user = address(0xBEEF);
        uint256 pay = amount * 0.065 ether + extra;
        vm.deal(user, pay);
        vm.startPrank(user);
        nft.mintNFTs{value: pay}(amount);
        vm.stopPrank();
        // Contract keeps ALL payment including overpayment
        assertEq(address(nft).balance, pay);
    }
}
