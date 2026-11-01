#!/usr/bin/env python3
"""Swap USDC -> WETH via ParaSwap"""
import json, urllib.request, sys
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://base-rpc.publicnode.com"))
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WETH = '0x4200000000000000000000000000000000000006'
PROXY = '0x93aAAe79a53759cD164340E4C8766E4Db5331cD7'

erc20 = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":False,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]

usdc = w3.eth.contract(address=USDC, abi=erc20)
usdc_bal = usdc.functions.balanceOf(WALLET).call()
print(f'USDC: {usdc_bal/1e6:.4f}')

# Approve
nonce = w3.eth.get_transaction_count(WALLET)
tx = usdc.functions.approve(PROXY, usdc_bal).build_transaction({
    'from': WALLET, 'nonce': nonce, 'gas': 60000,
    'gasPrice': w3.eth.gas_price, 'chainId': 8453,
})
s = w3.eth.account.sign_transaction(tx, PK)
r = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(s.raw_transaction), timeout=30)
print(f'Approve: {"OK" if r.status == 1 else "FAIL"}')

# Swap
url = f'https://api.paraswap.io/prices/?srcToken={USDC}&destToken={WETH}&amount={usdc_bal}&srcDecimals=6&destDecimals=18&side=SELL&network=8453&userAddress={WALLET}'
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
pr = json.loads(urllib.request.urlopen(req,timeout=10).read())['priceRoute']
dest = int(pr['destAmount'])/1e18
print(f'Dest: {dest:.10f} WETH')

payload = json.dumps({
    'srcToken': USDC, 'destToken': WETH, 'srcAmount': str(usdc_bal),
    'destAmount': pr['destAmount'], 'priceRoute': pr, 'userAddress': WALLET,
}).encode()
req2 = urllib.request.Request('https://api.paraswap.io/transactions/8453',
    data=payload, headers={'Content-Type':'application/json', 'User-Agent':'Mozilla/5.0'})
swap = json.loads(urllib.request.urlopen(req2,timeout=10).read())

nonce2 = w3.eth.get_transaction_count(WALLET)
exec_tx = {
    'to': swap['to'], 'data': swap['data'], 'value': int(swap.get('value',0)),
    'nonce': nonce2, 'gas': int(swap.get('gas', 300000)),
    'gasPrice': w3.eth.gas_price, 'chainId': 8453,
}
s2 = w3.eth.account.sign_transaction(exec_tx, PK)
tx_hash = w3.eth.send_raw_transaction(s2.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
print(f'Swap: {"OK" if receipt.status == 1 else "FAIL"} Gas: {receipt["gasUsed"]} Logs: {len(receipt.logs)}')
print(f'Tx: https://basescan.org/tx/{tx_hash.hex()}')

eth = w3.eth.get_balance(WALLET)/1e18
weth_b = int(w3.eth.call({'to':WETH,'data':'0x70a08231'+'0'*24+WALLET[2:]}), 16)/1e18
usdc_b = usdc.functions.balanceOf(WALLET).call()/1e6
print(f'ETH: {eth:.6f} | WETH: {weth_b:.10f} | USDC: {usdc_b:.4f}')
