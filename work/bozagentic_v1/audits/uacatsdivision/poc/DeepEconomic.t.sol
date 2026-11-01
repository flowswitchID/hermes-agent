// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract DeepEconomic is Test, IERC721Receiver {
    UACatsDivision nft;
    address owner = address(this);
    address user1 = address(0x1111);
    address user2 = address(0x2222);

    function setUp() public {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
        vm.deal(user1, 1000 ether);
        vm.deal(user2, 1000 ether);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    // ECON 1: Maximum ETH extractable by owner
    function test_max_owner_extraction() public {
        // All 10000 NFTs minted at exact price
        // 9901 via owner (free), 99 via user (paid)
        nft.mintNFTsOwner(9901);
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether * 99}(99);
        vm.stopPrank();

        uint256 contractBal = address(nft).balance;
        console.log("Max revenue (99 users * 0.065):", contractBal);
        console.log("Expected: 6.435 ETH (99 * 0.065)");

        // But if ALL 10000 minted by users (99 per user, ~101 users)
        // Revenue = 10000 * 0.065 = 650 ETH
        console.log("Max possible revenue: 650 ETH");
    }

    // ECON 2: Overpayment extraction — how much can owner steal?
    function test_overpayment_extraction() public {
        // 100 users each overpay by 1 ETH
        for (uint i = 0; i < 10; i++) {
            address user = address(uint160(0x1000 + i));
            vm.deal(user, 2 ether);
            vm.startPrank(user);
            nft.mintNFTs{value: 1.065 ether}(1); // overpay 1 ETH
            vm.stopPrank();
        }

        uint256 contractBal = address(nft).balance;
        console.log("Contract balance (10 overpayers):", contractBal);
        console.log("Legit revenue: 0.65 ETH");
        console.log("Stolen from users:", contractBal - 650000000000000000);

        // Owner drains ALL
        uint256 ownerBal = owner.balance;
        nft.withdraw();
        console.log("Owner extracted:", owner.balance - ownerBal);
    }

    // ECON 3: Can owner mint and sell for profit?
    function test_owner_profit() public {
        // Owner mints 100 free NFTs
        nft.mintNFTsOwner(100);
        // Owner can sell on secondary market
        // Cost: 0 (free mint)
        // Revenue: 100 * floor_price
        console.log("Owner free NFTs:", nft.balanceOf(owner));
        console.log("Owner cost: 0 ETH");
        console.log("This is standard for NFT projects (team allocation)");
    }

    // EDGE 1: What happens at exactly MAX_SUPPLY?
    function test_exact_max_supply() public {
        nft.mintNFTsOwner(9999);
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        assertEq(nft.totalSupply(), 10000);

        // Next mint should fail
        vm.startPrank(user2);
        vm.expectRevert("Not enough NFT left to mint");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        console.log("MAX_SUPPLY enforced correctly");
    }

    // EDGE 2: Multiple users minting simultaneously (race condition)
    function test_race_condition() public {
        nft.mintNFTsOwner(9998);
        // 2 NFTs left, 2 users try to mint 2 each
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether * 2}(2);
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert("Not enough NFT left to mint");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        console.log("RACE: First user gets remaining NFTs");
    }

    // EDGE 3: msg.value overflow check
    function test_msg_value_overflow() public {
        // amount * PRICE could overflow for large amounts
        // But amount <= 99 and PRICE = 0.065 ether
        // 99 * 0.065e18 = 6.435e18 < uint256 max
        // Safe
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether * 99}(99);
        vm.stopPrank();
        assertEq(nft.balanceOf(user1), 99);
        console.log("No overflow at max amount");
    }

    // EDGE 4: Can user mint with exact wei precision?
    function test_exact_wei() public {
        vm.startPrank(user1);
        // Exactly 0.065 ether = 65000000000000000 wei
        nft.mintNFTs{value: 65000000000000000}(1);
        vm.stopPrank();
        assertEq(nft.balanceOf(user1), 1);
        assertEq(address(nft).balance, 65000000000000000);
        console.log("Exact wei payment works");
    }

    // EDGE 5: 1 wei under payment
    function test_one_wei_under() public {
        vm.startPrank(user1);
        vm.expectRevert("Not enough ether to purchase NFT");
        nft.mintNFTs{value: 65000000000000000 - 1}(1);
        vm.stopPrank();
        console.log("1 wei under payment rejected");
    }

    // EDGE 6: Owner renounceOwnership — then withdraw impossible
    function test_renounce_ownership() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 1 ether}(1);
        vm.stopPrank();

        console.log("Balance before renounce:", address(nft).balance);

        // Owner renounces
        nft.renounceOwnership();

        // Now withdraw is impossible — funds LOCKED forever
        console.log("Owner after renounce:", nft.owner());
        console.log("Funds LOCKED forever:", address(nft).balance);
        console.log("CRITICAL if owner renounces before withdraw!");
    }

    // EDGE 7: Transfer ownership to dead address
    function test_dead_owner() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 1 ether}(1);
        vm.stopPrank();

        // Transfer to dead address
        nft.transferOwnership(0x000000000000000000000000000000000000dEaD);
        console.log("New owner:", nft.owner());
        console.log("Funds LOCKED: dead address can't withdraw");
    }

    receive() external payable {}
}
