#!/usr/bin/env python3
"""Test Uniswap V3 swap with web3.py ABI encoding"""
from web3 import Web3
import json, time

RPC = 'https://base-rpc.publicnode.com'
w3 = Web3(Web3.HTTPProvider(RPC))

ROUTER = '0xE592427A0AEce92De3Edee1F18E0157C05861564'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'

# Router ABI (exactInputSingle only)
router_abi = [{"inputs":[{"components":[{"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},{"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},{"name":"deadline","type":"uint256"},{"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},{"name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct ISwapRouter.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]

router = w3.eth.contract(address=ROUTER, abi=router_abi)

# ERC20 minimal ABI for balanceOf
erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
usdc_contract = w3.eth.contract(address=USDC, abi=erc20_abi)

amount = Web3.to_wei(0.0000533, 'ether')
print(f'ETH balance: {w3.eth.get_balance(WALLET)/1e18:.6f}')
print(f'USDC balance: {usdc_contract.functions.balanceOf(WALLET).call()/1e6:.4f}')
print(f'Swapping {amount/1e18} ETH -> USDC...')

nonce = w3.eth.get_transaction_count(WALLET)
block = w3.eth.get_block('latest')

tx = router.functions.exactInputSingle({
    'tokenIn': Web3.to_checksum_address(WETH),
    'tokenOut': Web3.to_checksum_address(USDC),
    'fee': 3000,
    'recipient': Web3.to_checksum_address(WALLET),
    'deadline': block['timestamp'] + 300,
    'amountIn': amount,
    'amountOutMinimum': 1,
    'sqrtPriceLimitX96': 0,
}).build_transaction({
    'from': WALLET,
    'value': amount,
    'nonce': nonce,
    'gas': 200000,
    'gasPrice': w3.eth.gas_price,
    'chainId': 8453,
})

signed = w3.eth.account.sign_transaction(tx, PK)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'Tx: {tx_hash.hex()}')

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
eth_after = w3.eth.get_balance(WALLET)/1e18
usdc_after = usdc_contract.functions.balanceOf(WALLET).call()/1e6

print(f'\nStatus: {"✅ SUCCESS" if receipt.status == 1 else "❌ FAILED"}')
print(f'Gas: {receipt["gasUsed"]}')
print(f'Logs: {len(receipt.logs)}')
print(f'ETH: {eth_after:.6f}')
print(f'USDC: {usdc_after:.4f}')
print(f'Basescan: https://basescan.org/tx/{tx_hash.hex()}')
