#!/usr/bin/env python3
"""Swap via Universal Router — CORRECT encoding (from user's tx)"""
from eth_abi import encode
from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider('https://base-rpc.publicnode.com'))
WALLET = Web3.to_checksum_address('0xWALLET_ADDR_REDACTED')
PK = 'PK_REDACTED_USE_ENV_VAR'
ROUTER = Web3.to_checksum_address('0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7')
PERMIT2 = Web3.to_checksum_address('0x000000000022D473030F116dDEE9F6B43aC78BA3')
USDC = Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
WETH = Web3.to_checksum_address('0x4200000000000000000000000000000000000006')

erc20 = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"},
         {"constant":False,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"type":"function"},
         {"constant":True,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"type":"uint256"}],"type":"function"}]

usdc = w3.eth.contract(address=USDC, abi=erc20)
usdc_bal = usdc.functions.balanceOf(WALLET).call()
weth = w3.eth.contract(address=WETH, abi=erc20)
weth_bal = weth.functions.balanceOf(WALLET).call()

if usdc_bal > 0:
    TOKEN_IN, TOKEN_OUT, AMOUNT = USDC, WETH, usdc_bal
    token_name = 'USDC'
elif weth_bal > 0:
    TOKEN_IN, TOKEN_OUT, AMOUNT = WETH, USDC, weth_bal
    token_name = 'WETH'
else:
    print('No tokens to swap')
    exit()

print(f'Swapping {AMOUNT/1e6 if token_name == "USDC" else AMOUNT/1e18:.4f} {token_name}')

nonce = w3.eth.get_transaction_count(WALLET)

# Build execute() — from user's tx2
print('\nBuilding execute()...')

# Path: TOKEN_IN -> fee 100 (0.01%) -> TOKEN_OUT
path = bytes.fromhex(TOKEN_IN[2:]) + (100).to_bytes(3, 'big') + bytes.fromhex(TOKEN_OUT[2:])
swap_input = encode(['address','uint256','uint256','bytes','bool'],
    [WALLET, AMOUNT, 1, path, True])

commands = bytes([0x00])  # V3_SWAP_EXACT_IN only
inputs = [swap_input]
deadline = w3.eth.get_block('latest')['timestamp'] + 600

all_encoded = encode(['bytes', 'bytes[]', 'uint256'], [commands, inputs, deadline])
calldata = '0x3593564c' + all_encoded.hex()

print(f'Swap via UniV3 0.01% pool')

exec_tx = {
    'to': ROUTER, 'data': calldata, 'value': 0,
    'nonce': nonce, 'gas': 300000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
}
s2 = w3.eth.account.sign_transaction(exec_tx, PK)
tx_hash = w3.eth.send_raw_transaction(s2.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

print(f'\nSwap: {" BERHASIL!" if receipt.status==1 else "FAIL"}')
print(f'Gas: {receipt["gasUsed"]} Logs: {len(receipt.logs)}')
print(f'Tx: https://basescan.org/tx/{tx_hash.hex()}')

eth_after = w3.eth.get_balance(WALLET)/1e18
usdc_bal = usdc.functions.balanceOf(WALLET).call()/1e6
weth_bal_after = weth.functions.balanceOf(WALLET).call()/1e18
print(f'\nETH: {eth_after:.6f} | WETH: {weth_bal_after:.8f} | USDC: {usdc_bal:.4f}')
