// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnProxy {
    address public impl;
    function setImpl(address _impl) external { impl = _impl; }

    function forward(bytes calldata data) external returns (bytes memory) {
        (bool ok, bytes memory ret) = impl.delegatecall(data);
        require(ok);
        return ret;
    }
}
