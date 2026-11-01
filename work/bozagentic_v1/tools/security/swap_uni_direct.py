#!/usr/bin/env python3
"""Swap via Universal Router execute() — encoding manual"""
from eth_abi import encode
from web3 import Web3
import json, urllib.request

w3 = Web3(Web3.HTTPProvider('https://base-rpc.publicnode.com'))
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
ROUTER = Web3.to_checksum_address('0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7')
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WETH = '0x4200000000000000000000000000000000000006'
PROXY = '0x93aAAe79a53759cD164340E4C8766E4Db5331cD7'

erc20 = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"},{"constant":False,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"type":"function"}]
usdc = w3.eth.contract(address=USDC, abi=erc20)
weth = w3.eth.contract(address=WETH, abi=erc20)

weth_bal = weth.functions.balanceOf(WALLET).call()
print(f'WETH: {weth_bal/1e18:.8f}')

if weth_bal == 0:
    print('No WETH to swap')
    exit()

# Approve Universal Router for WETH
nonce = w3.eth.get_transaction_count(WALLET)
tx = weth.functions.approve(ROUTER, weth_bal).build_transaction({
    'from':WALLET,'nonce':nonce,'gas':60000,'gasPrice':w3.eth.gas_price,'chainId':8453})
s = w3.eth.account.sign_transaction(tx, PK)
r = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(s.raw_transaction),timeout=30)
print(f'Approve Router: {"OK" if r.status==1 else "FAIL"}')

# Path: WETH -> USDC (fee 3000)
path = bytes.fromhex(WETH[2:]) + (3000).to_bytes(3, 'big') + bytes.fromhex(USDC[2:])
input0 = encode(['address','uint256','uint256','bytes','bool'], 
    [WALLET, weth_bal, 1, path, True])

# SWEEP: send USDC to wallet
input1 = encode(['address','address','uint256'], [USDC, WALLET, 1])

commands = bytes([0x0b, 0x10])  # V3_SWAP_EXACT_IN + SWEEP
inputs = [input0, input1]
deadline = w3.eth.get_block('latest')['timestamp'] + 300

all_encoded = encode(['bytes', 'bytes[]', 'uint256'], [commands, inputs, deadline])
calldata = bytes.fromhex('3593564c') + all_encoded

print(f'Commands: {commands.hex()}')
print(f'Path: WETH -> fee 3000 -> USDC')

exec_tx = {
    'to': ROUTER, 'data': '0x' + calldata.hex(), 'value': 0,
    'nonce': nonce+1, 'gas': 300000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
}
s2 = w3.eth.account.sign_transaction(exec_tx, PK)
tx_hash = w3.eth.send_raw_transaction(s2.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

print(f'\nSwap: {"OK" if receipt.status==1 else "FAIL"}')
print(f'Gas: {receipt["gasUsed"]} Logs: {len(receipt.logs)}')
if receipt.status == 1:
    print(f'✅ UNIVERSAL ROUTER ENCODING BERHASIL!')
print(f'Tx: https://basescan.org/tx/{tx_hash.hex()}')
