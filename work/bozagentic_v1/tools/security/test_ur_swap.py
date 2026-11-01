#!/usr/bin/env python3
"""Swap via Universal Router on Base"""
from web3 import Web3
from eth_abi import encode
import json

RPC = 'https://base-rpc.publicnode.com'
w3 = Web3(Web3.HTTPProvider(RPC))

UROUTER = '0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'

# Universal Router execute ABI
ur_abi = json.loads('[{"inputs":[{"name":"commands","type":"bytes"},{"name":"inputs","type":"bytes[]"},{"name":"deadline","type":"uint256"}],"name":"execute","outputs":[],"stateMutability":"payable","type":"function"}]')
ur = w3.eth.contract(address=UROUTER, abi=ur_abi)

erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
usdc = w3.eth.contract(address=USDC, abi=erc20_abi)

amount = Web3.to_wei(0.0000533, 'ether')
print(f'ETH: {w3.eth.get_balance(WALLET)/1e18:.6f}')
print(f'USDC: {usdc.functions.balanceOf(WALLET).call()/1e6:.4f}')
print(f'Swap {amount/1e18} ETH -> USDC via Universal Router...')

# Command: V3_SWAP_EXACT_IN = 0x00
# Input: abi.encode(recipient, amountIn, amountOutMin, path, payerIsUser)
# Path: WETH + fee(3000) + USDC

path = Web3.to_bytes(hexstr=WETH) + (3000).to_bytes(3, 'big') + Web3.to_bytes(hexstr=USDC)
input_data = encode(['address', 'uint256', 'uint256', 'bytes', 'bool'], [WALLET, amount, 1, path, False])

commands = bytes([0x00])
deadline = w3.eth.get_block('latest')['timestamp'] + 300

nonce = w3.eth.get_transaction_count(WALLET)
tx = ur.functions.execute(commands, [input_data], deadline).build_transaction({
    'from': WALLET,
    'value': amount,
    'nonce': nonce,
    'gas': 300000,
    'gasPrice': w3.eth.gas_price,
    'chainId': 8453,
})

signed = w3.eth.account.sign_transaction(tx, PK)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'Tx: {tx_hash.hex()}')

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
print(f'Status: {"✅" if receipt.status == 1 else "❌"}')
print(f'Gas: {receipt["gasUsed"]}')
print(f'Logs: {len(receipt.logs)}')

eth_after = w3.eth.get_balance(WALLET)/1e18
usdc_after = usdc.functions.balanceOf(WALLET).call()/1e6
print(f'ETH: {eth_after:.6f}')
print(f'USDC: {usdc_after:.4f}')
