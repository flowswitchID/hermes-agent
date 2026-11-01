// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "forge-std/Test.sol";
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

/**
 * @title PoC: Overpayment in mintNFTs() Not Refunded
 * @target UACatsDivision 0xb95712AC7Fbf54Ab3FD10C86FD1e9463C8461bf5
 * @severity LOW
 * @category Business Logic Errors
 *
 * RUN:
 *   forge init uacd-poc && cd uacd-poc
 *   forge install OpenZeppelin/openzeppelin-contracts@v4.8.0 --no-git
 *   echo "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/" > remappings.txt
 *   Copy UACatsDivision.sol to src/
 *   Copy this file to test/
 *   forge test --match-contract OverpaymentPoC -vvv
 */

contract OverpaymentPoC is Test, IERC721Receiver {
    UACatsDivision nft;
    address user = address(0x1111);

    function setUp() public {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
        vm.deal(user, 10 ether);
    }

    function onERC721Received(address, address, uint256, bytes calldata)
        external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    // PROOF 1: Overpayment is NOT refunded
    function test_overpayment_not_refunded() public {
        vm.startPrank(user);
        uint256 balBefore = user.balance;
        nft.mintNFTs{value: 1 ether}(1); // NFT costs 0.065 ETH
        uint256 spent = balBefore - user.balance;
        vm.stopPrank();

        assertEq(spent, 1 ether, "User paid full 1 ETH");
        assertEq(address(nft).balance, 1 ether, "Contract keeps ALL");
        // 0.935 ETH LOST - no refund mechanism exists
    }

    // PROOF 2: Owner extracts overpayment via withdraw()
    function test_owner_extracts_overpayment() public {
        vm.startPrank(user);
        nft.mintNFTs{value: 5 ether}(1); // overpay 4.935 ETH
        vm.stopPrank();

        uint256 ownerBal = address(this).balance;
        nft.withdraw();
        uint256 received = address(this).balance - ownerBal;

        assertEq(received, 5 ether, "Owner gets ALL including overpayment");
        assertEq(address(nft).balance, 0, "Contract drained");
    }

    // PROOF 3: Multiple users overpay - owner gets everything
    function test_multiple_overpayments() public {
        for (uint i = 0; i < 5; i++) {
            address u = address(uint160(0x1000 + i));
            vm.deal(u, 2 ether);
            vm.startPrank(u);
            nft.mintNFTs{value: 1.065 ether}(1); // overpay 1 ETH each
            vm.stopPrank();
        }

        // 5 users * 0.065 legit + 5 users * 1.0 overpayment
        assertEq(address(nft).balance, 5.325 ether);

        uint256 ownerBal = address(this).balance;
        nft.withdraw();
        assertEq(address(this).balance - ownerBal, 5.325 ether);
    }

    // PROOF 4: Exact payment works correctly (no bug)
    function test_exact_payment_ok() public {
        vm.startPrank(user);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();

        assertEq(nft.balanceOf(user), 1);
        assertEq(address(nft).balance, 0.065 ether);
    }

    receive() external payable {}
}
