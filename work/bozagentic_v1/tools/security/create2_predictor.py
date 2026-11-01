#!/usr/bin/env python3
"""BOZAGENTIC CREATE2 Address Predictor v1.0"""
import sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com", request_kwargs={'timeout': 10}))

def predict_create2(deployer, salt, init_code_hash):
    """Predict CREATE2 address"""
    factory_bytes = bytes.fromhex(deployer.replace('0x','').lower())
    salt_bytes = bytes.fromhex(salt.replace('0x','').lower().zfill(64))
    init_hash_bytes = bytes.fromhex(init_code_hash.replace('0x',''))
    data = b'\xff' + factory_bytes + salt_bytes + init_hash_bytes
    return Web3.to_checksum_address('0x' + Web3.keccak(data)[-20:].hex())

# Uniswap V2 pair prediction
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
UNISWAP_V2_INIT_CODE_HASH = "0x96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f"

def predict_uniswap_v2_pair(token_a, token_b):
    """Predict Uniswap V2 pair address"""
    t0 = token_a if int(token_a, 16) < int(token_b, 16) else token_b
    t1 = token_b if int(token_a, 16) < int(token_b, 16) else token_a
    salt = Web3.keccak(
        bytes.fromhex(t0[2:].lower().zfill(64)) +
        bytes.fromhex(t1[2:].lower().zfill(64))
    )
    return predict_create2(UNISWAP_V2_FACTORY, salt.hex(), UNISWAP_V2_INIT_CODE_HASH)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        print(predict_uniswap_v2_pair(sys.argv[1], sys.argv[2]))
    else:
        # Default: USDC/WETH
        USDC = "0xA0b86991c627Ce246199B89fF4b35b54C5c85687"
        WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        print(f"USDC/WETH: {predict_uniswap_v2_pair(USDC, WETH)}")
