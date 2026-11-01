// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {CoinbaseSmartWallet} from "../../src/CoinbaseSmartWallet.sol";
import {CoinbaseSmartWalletFactory} from "../../src/CoinbaseSmartWalletFactory.sol";

contract HalmosProperties {
    CoinbaseSmartWallet wallet;
    CoinbaseSmartWalletFactory factory;
    
    constructor() {
        CoinbaseSmartWallet impl = new CoinbaseSmartWallet();
        factory = new CoinbaseSmartWalletFactory(address(impl));
        
        bytes[] memory owners = new bytes[](1);
        owners[0] = abi.encode(address(this));
        wallet = CoinbaseSmartWallet(payable(factory.createAccount(owners, 0)));
    }
    
    // Property: ownerCount is always >= 1 after init
    function check_ownerCount_positive() external view {
        assert(wallet.ownerCount() >= 1);
    }
    
    // Property: isOwnerAddress returns true for actual owner
    function check_isOwner() external view {
        assert(wallet.isOwnerAddress(address(this)));
    }
    
    // Property: cannot add zero address as owner
    function check_noZeroOwner() external {
        try wallet.addOwnerAddress(address(0)) {
            assert(false);
        } catch {
            // expected
        }
    }
}
