// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.30;

import {IERC721} from "@openzeppelin/contracts/token/ERC721/IERC721.sol";

interface IftPUT is IERC721 {
    struct Put {
        // slot 0
        address token; // 20: the denomination of asset
        uint96 amount; // 12: the amount of denomination asset
        // slot 1
        uint96 ft; // 12: updating value of FT for calcs
        uint96 ft_bought; // 12: amount of FT originally bought
        // (8 bytes unused)

        // slot 2
        uint96 withdrawn; // 12: amount of FT that has been withdrawn
        uint96 burned; // 12: amount of FT that has been burned via excercising the PUT option
        // (8 bytes unused)

        // slot 3
        uint96 strike; // 12: the exchange rate of FT / amount
        uint96 amountRemaining; // 12: amount of denomination asset remaining
        uint64 ftPerUSD; // 8: the ftPerUSD at time of purchase
    }

    function puts(uint256 tokenId) external view returns (Put memory);
}
