// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "forge-std/Test.sol";
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract DeepAttacks is Test, IERC721Receiver {
    UACatsDivision nft;
    address owner = address(this);
    address user1 = address(0x1111);

    function setUp() public {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
        vm.deal(user1, 1000 ether);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    // ATTACK 1: Gas griefing via _safeMint loop
    // If attacker deploys contract that returns slowly in onERC721Received
    // mintNFTs(99) does 99 _safeMint calls, each calling onERC721Received
    // Gas cost = 99 * (gas per mint + callback gas)
    function test_gas_griefing() public {
        GasGriefer griefer = new GasGriefer(address(nft));
        vm.deal(address(griefer), 100 ether);
        uint256 gasBefore = gasleft();
        griefer.griefMint{value: 0.065 ether * 5}(5);
        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for 5 mints with griefer:", gasUsed);
        console.log("Griefer NFT balance:", nft.balanceOf(address(griefer)));
    }

    // ATTACK 2: Front-running mintNFTsOwner
    // Owner calls mintNFTsOwner(100)
    // Attacker sees in mempool, front-runs with mintNFTs(99)
    // If supply is near MAX, owner's tx fails
    function test_frontrun_owner_mint() public {
        // Set supply to 9901
        nft.mintNFTsOwner(9901);
        assertEq(nft.totalSupply(), 9901);

        // Attacker front-runs: mints 99 (max per account)
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether * 99}(99);
        vm.stopPrank();
        assertEq(nft.totalSupply(), 10000);

        // Owner's mintNFTsOwner now fails
        vm.expectRevert("Not enough tokens left to mint");
        nft.mintNFTsOwner(1);
        console.log("FRONTRUN: Owner mint blocked by user mint");
    }

    // ATTACK 3: Metadata rug — owner changes baseURI after mint
    function test_metadata_rug() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();

        string memory uriBefore = nft.tokenURI(1);
        console.log("URI before:", uriBefore);

        // Owner changes baseURI
        nft.setBaseURI("ipfs://EVIL_HASH/");
        string memory uriAfter = nft.tokenURI(1);
        console.log("URI after:", uriAfter);

        // Metadata changed! NFT art/description can be replaced
        console.log("METADATA RUG: Owner can change ALL NFT metadata");
    }

    // ATTACK 4: contractURI rug — marketplace-level metadata
    function test_contractURI_rug() public {
        string memory before_ = nft.contractURI();
        console.log("contractURI before:", before_);
        nft.setContractURI("ipfs://EVIL_CONTRACT/");
        string memory after_ = nft.contractURI();
        console.log("contractURI after:", after_);
        console.log("CONTRACT URI RUG: Owner can change collection metadata");
    }

    // ATTACK 5: Withdraw reentrancy via malicious owner contract
    // withdraw() uses msg.sender.call{value:balance}("")
    // If owner is a contract with receive() that re-enters...
    // BUT: withdraw is onlyOwner, and owner is EOA on mainnet
    // AND: no state changes after the call (CEI violation but no state to corrupt)
    function test_withdraw_reentrancy() public {
        // Deploy malicious owner
        MaliciousOwner malOwner = new MaliciousOwner(address(nft));
        nft.transferOwnership(address(malOwner));

        // Fund the contract
        vm.startPrank(user1);
        nft.mintNFTs{value: 1 ether}(1);
        vm.stopPrank();
        console.log("Contract balance:", address(nft).balance);

        // Malicious owner withdraws — tries reentrancy
        malOwner.attackWithdraw();
        console.log("Contract balance after:", address(nft).balance);
        console.log("Malicious owner balance:", address(malOwner).balance);
        // Reentrancy doesn't help because:
        // 1. balance is read once at start
        // 2. No state changes after call
        // 3. Second call would have balance = 0
    }

    // ATTACK 6: ERC721 approval phishing
    // User approves malicious contract -> NFT stolen
    // This is inherent to ERC721, not a contract bug
    function test_approval_phishing() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        // User approves malicious contract
        address phishing = address(0xDEAD);
        nft.approve(phishing, 1);
        vm.stopPrank();

        // Phishing contract can now transfer NFT
        assertEq(nft.getApproved(1), phishing);
        console.log("APPROVAL PHISHING: User approved malicious contract");
        console.log("This is ERC721 spec behavior, not a bug");
    }

    // ATTACK 7: No ERC2981 royalties — marketplace can't enforce
    function test_no_royalties() public view {
        // Check if contract supports ERC2981
        (bool ok,) = address(nft).staticcall(abi.encodeWithSignature("supportsInterface(bytes4)", 0x2a55205a));
        console.log("ERC2981 supported:", ok);
        console.log("NO ROYALTIES: Marketplaces can't enforce creator fees");
    }

    // ATTACK 8: No ERC721Enumerable — can't enumerate tokens
    function test_no_enumerable() public view {
        (bool ok,) = address(nft).staticcall(abi.encodeWithSignature("supportsInterface(bytes4)", 0x780e9d63));
        console.log("ERC721Enumerable supported:", ok);
    }

    // ATTACK 9: Sale can be toggled anytime — users mid-tx get reverted
    function test_sale_toggle_grief() public {
        vm.startPrank(user1);
        vm.expectRevert("Sale is closed");
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        console.log("SALE TOGGLE: Owner can grief users mid-mint");
    }

    // ATTACK 10: _currentId starts at 0, first token is 1
    // No token 0 exists — but some marketplaces assume 0-indexed
    function test_token_indexing() public {
        vm.startPrank(user1);
        nft.mintNFTs{value: 0.065 ether}(1);
        vm.stopPrank();
        // First token is ID 1, not 0
        assertEq(nft.ownerOf(1), user1);
        vm.expectRevert("ERC721: invalid token ID");
        nft.ownerOf(0);
        console.log("TOKEN INDEXING: 1-indexed, token 0 doesn't exist");
    }

    receive() external payable {}
}

contract GasGriefer is IERC721Receiver {
    UACatsDivision nft;
    constructor(address _nft) { nft = UACatsDivision(_nft); }

    function griefMint(uint amount) external payable {
        nft.mintNFTs{value: msg.value}(amount);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        // Burn gas in callback
        uint256 x;
        for (uint i = 0; i < 1000; i++) {
            x += i * i;
        }
        // Prevent optimization
        require(x > 0 || x == 0);
        return IERC721Receiver.onERC721Received.selector;
    }
}

contract MaliciousOwner {
    UACatsDivision nft;
    uint256 public attackCount;

    constructor(address _nft) { nft = UACatsDivision(_nft); }

    function attackWithdraw() external {
        nft.withdraw();
    }

    receive() external payable {
        if (attackCount < 3 && address(nft).balance > 0) {
            attackCount++;
            try nft.withdraw() {} catch {}
        }
    }
}
