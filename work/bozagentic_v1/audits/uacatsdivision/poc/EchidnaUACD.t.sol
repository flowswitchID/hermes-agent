// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;
import "../src/UACatsDivision.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";

contract EchidnaUACD is IERC721Receiver {
    UACatsDivision nft;

    constructor() {
        nft = new UACatsDivision("ipfs://base/", "ipfs://contract/");
        nft.activateSales(true);
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    function fuzz_mint(uint8 amount) public {
        if (amount == 0 || amount > 10) return;
        uint256 supplyBefore = nft.totalSupply();
        if (supplyBefore + amount > 10000) return;
        uint256 pay = uint256(amount) * 0.065 ether;
        nft.mintNFTs{value: pay}(amount);
        assert(nft.totalSupply() == supplyBefore + amount);
    }

    function fuzz_owner_mint(uint8 amount) public {
        if (amount == 0 || amount > 10) return;
        uint256 supplyBefore = nft.totalSupply();
        if (supplyBefore + amount > 10000) return;
        nft.mintNFTsOwner(amount);
        assert(nft.totalSupply() == supplyBefore + amount);
    }

    function echidna_max_supply() public view returns (bool) {
        return nft.totalSupply() <= 10000;
    }

    receive() external payable {}
}
