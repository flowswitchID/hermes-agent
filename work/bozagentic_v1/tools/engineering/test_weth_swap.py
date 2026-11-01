#!/usr/bin/env python3
"""Swap ETH -> USDC via WETH wrapping + SwapRouter"""
from web3 import Web3

RPC = 'https://base-rpc.publicnode.com'
w3 = Web3(Web3.HTTPProvider(RPC))

WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
ROUTER = '0xE592427A0AEce92De3Edee1F18E0157C05861564'
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

erc20 = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"},{"constant":False,"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"type":"function"}]
weth_abi = erc20 + [{"constant":False,"inputs":[],"name":"deposit","outputs":[],"type":"function","stateMutability":"payable"},{"constant":False,"inputs":[{"name":"wad","type":"uint256"}],"name":"withdraw","outputs":[],"type":"function"}]
router_abi = [{"inputs":[{"components":[{"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},{"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},{"name":"deadline","type":"uint256"},{"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},{"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],"name":"exactInputSingle","outputs":[{"name":"amountOut","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]

usdc = w3.eth.contract(address=USDC, abi=erc20)
weth = w3.eth.contract(address=WETH, abi=weth_abi)
router = w3.eth.contract(address=ROUTER, abi=router_abi)

amount = Web3.to_wei(0.0000533, 'ether')

print(f'ETH: {w3.eth.get_balance(WALLET)/1e18:.6f}')
print(f'WETH: {weth.functions.balanceOf(WALLET).call()/1e18:.6f}')
print(f'USDC: {usdc.functions.balanceOf(WALLET).call()/1e6:.4f}')

# Step 1: Wrap ETH -> WETH
print(f'\nStep 1: Wrap {amount/1e18} ETH -> WETH...')
wrap_tx = weth.functions.deposit().build_transaction({
    'from': WALLET, 'value': amount, 'nonce': w3.eth.get_transaction_count(WALLET),
    'gas': 100000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
})
signed = w3.eth.account.sign_transaction(wrap_tx, PK)
tx1 = w3.eth.send_raw_transaction(signed.raw_transaction)
r1 = w3.eth.wait_for_transaction_receipt(tx1, timeout=30)
print(f'  Status: {"✅" if r1.status == 1 else "❌"} Gas: {r1["gasUsed"]}')

weth_bal = weth.functions.balanceOf(WALLET).call()
print(f'  WETH: {weth_bal/1e18:.6f}')

# Step 2: Approve Router for WETH
if weth_bal > 0:
    print(f'\nStep 2: Approve Router...')
    app_tx = weth.functions.approve(ROUTER, weth_bal).build_transaction({
        'from': WALLET, 'nonce': w3.eth.get_transaction_count(WALLET),
        'gas': 60000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
    })
    signed = w3.eth.account.sign_transaction(app_tx, PK)
    tx2 = w3.eth.send_raw_transaction(signed.raw_transaction)
    r2 = w3.eth.wait_for_transaction_receipt(tx2, timeout=30)
    print(f'  Status: {"✅" if r2.status == 1 else "❌"}')
    
    # Step 3: Swap WETH -> USDC
    print(f'\nStep 3: Swap WETH -> USDC...')
    block = w3.eth.get_block('latest')
    swap_tx = router.functions.exactInputSingle({
        'tokenIn': WETH, 'tokenOut': USDC, 'fee': 3000,
        'recipient': WALLET, 'deadline': block['timestamp'] + 300,
        'amountIn': weth_bal, 'amountOutMinimum': 1, 'sqrtPriceLimitX96': 0,
    }).build_transaction({
        'from': WALLET, 'nonce': w3.eth.get_transaction_count(WALLET),
        'gas': 200000, 'gasPrice': w3.eth.gas_price, 'chainId': 8453,
    })
    signed = w3.eth.account.sign_transaction(swap_tx, PK)
    tx3 = w3.eth.send_raw_transaction(signed.raw_transaction)
    r3 = w3.eth.wait_for_transaction_receipt(tx3, timeout=30)
    print(f'  Status: {"✅" if r3.status == 1 else "❌"} Gas: {r3["gasUsed"]} Logs: {len(r3.logs)}')

print(f'\nFinal:')
print(f'ETH: {w3.eth.get_balance(WALLET)/1e18:.6f}')
print(f'WETH: {weth.functions.balanceOf(WALLET).call()/1e18:.6f}')
print(f'USDC: {usdc.functions.balanceOf(WALLET).call()/1e6:.4f}')
