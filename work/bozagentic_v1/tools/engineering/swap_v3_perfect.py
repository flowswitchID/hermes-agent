#!/usr/bin/env python3
"""Swap via Universal Router — PERFECT encoding"""
from eth_abi import encode
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://base-rpc.publicnode.com'))
WALLET = Web3.to_checksum_address('0xWALLET_ADDR_REDACTED')
PK = 'PK_REDACTED_USE_ENV_VAR'
ROUTER = Web3.to_checksum_address('0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7')
USDC = Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
WETH = Web3.to_checksum_address('0x4200000000000000000000000000000000000006')

weth = w3.eth.contract(address=WETH, abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"}])
usdc = w3.eth.contract(address=USDC, abi=[{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"}])

weth_bal = weth.functions.balanceOf(WALLET).call()
usdc_bal = usdc.functions.balanceOf(WALLET).call()

if weth_bal > 0:
    TOKEN_IN, TOKEN_OUT, AMOUNT = WETH, USDC, weth_bal
    FEE = 100  # 0.01%
    token_name = 'WETH'
elif usdc_bal > 0:
    TOKEN_IN, TOKEN_OUT, AMOUNT = USDC, WETH, usdc_bal
    FEE = 300  # 0.03%
    token_name = 'USDC'
else:
    print('No tokens to swap')
    exit()

print(f'{token_name}: {AMOUNT/1e6 if token_name=="USDC" else AMOUNT/1e18:.6f}')

nonce = w3.eth.get_transaction_count(WALLET)

# --- Command 0x0a: Permit2 transfer from ---
expiration = w3.eth.get_block('latest')['timestamp'] + 3600  # 1 hour
sig_deadline = w3.eth.get_block('latest')['timestamp'] + 600
# Empty signature (65 bytes, all zeros)
sig = b'\x00' * 65

permit_input = encode(
    ['address', 'uint160', 'uint48', 'uint48', 'address', 'uint256', 'bytes'],
    [TOKEN_IN, 2**160 - 1, expiration, 0, ROUTER, sig_deadline, sig]
)
print(f'Permit input: {len(permit_input)} bytes')

# --- Command 0x00: V3_SWAP_EXACT_IN ---
path = bytes.fromhex(TOKEN_IN[2:]) + FEE.to_bytes(3, 'big') + bytes.fromhex(TOKEN_OUT[2:])
swap_input = encode(['address','uint256','uint256','bytes','bool'],
    [WALLET, AMOUNT, 1, path, True])

commands = bytes([0x0a, 0x00])
inputs = [permit_input, swap_input]
deadline = w3.eth.get_block('latest')['timestamp'] + 600

all_encoded = encode(['bytes', 'bytes[]', 'uint256'], [commands, inputs, deadline])
calldata = '0x3593564c' + all_encoded.hex()

print(f'Swap {token_name} -> fee {FEE/10000:.2f}% -> WETH/USDC')

exec_tx = {
    'to': ROUTER, 'data': calldata, 'value': 0,
    'nonce': nonce, 'gas': 300000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
}
s = w3.eth.account.sign_transaction(exec_tx, PK)
tx_hash = w3.eth.send_raw_transaction(s.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

print(f'Swap: {" BERHASIL!" if receipt.status==1 else "FAIL"}')
print(f'Gas: {receipt["gasUsed"]} Logs: {len(receipt.logs)}')
if receipt.status == 1:
    eth_a = w3.eth.get_balance(WALLET)/1e18
    usdc_a = usdc.functions.balanceOf(WALLET).call()/1e6
    weth_a = weth.functions.balanceOf(WALLET).call()/1e18
    print(f'ETH: {eth_a:.6f} | WETH: {weth_a:.8f} | USDC: {usdc_a:.4f}')
print(f'Tx: https://basescan.org/tx/{tx_hash.hex()}')
