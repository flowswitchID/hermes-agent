#!/usr/bin/env python3
"""
BOZAGENTIC — Flash Loan + ParaSwap Arbitrage
Execute: python3 flash_loan_paraswap.py <amount_usdc>
"""
import json, urllib.request, sys
from web3 import Web3

# Config
RPC = 'https://base-rpc.publicnode.com'
w3 = Web3(Web3.HTTPProvider(RPC))
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WETH = '0x4200000000000000000000000000000000000006'
PROXY = '0x93aAAe79a53759cD164340E4C8766E4Db5331cD7'
AAVE_POOL = '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5'

def get_paraswap_quote(src, dst, amount, src_dec, dst_dec):
    """Get quote from ParaSwap and return tx data"""
    url = f'https://api.paraswap.io/prices/?srcToken={src}&destToken={dst}&amount={amount}&srcDecimals={src_dec}&destDecimals={dst_dec}&side=SELL&network=8453&userAddress={WALLET}'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req,timeout=10).read())['priceRoute']

def get_paraswap_tx(price_route, src, dst, amount, dest_amount):
    """Get transaction data from ParaSwap"""
    payload = json.dumps({
        'srcToken': src, 'destToken': dst, 'srcAmount': str(amount),
        'destAmount': dest_amount, 'priceRoute': price_route,
        'userAddress': WALLET,
    }).encode()
    req = urllib.request.Request('https://api.paraswap.io/transactions/8453',
        data=payload, headers={'Content-Type':'application/json', 'User-Agent':'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req,timeout=10).read())

# USDC ABI for approval
erc20 = [{"constant":True,"inputs":[{"_owner":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"},{"constant":False,"inputs":[{"spender":"address"},{"amount":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"type":"function"}]
usdc = w3.eth.contract(address=USDC, abi=erc20)

# Main
amount_usdc = int(sys.argv[1]) if len(sys.argv) > 1 else 1000000  # default $1
print(f'Flash loan: ${amount_usdc/1e6} USDC')

# Get quote for USDC -> WETH (buy cheap)
print('\nQuote USDC->WETH...')
route1 = get_paraswap_quote(USDC, WETH, amount_usdc, 6, 18)
weth_out = int(route1['destAmount'])
print(f'  -> {weth_out/1e18:.6f} WETH')

# Get quote for WETH -> USDC (sell expensive)
print('Quote WETH->USDC...')
route2 = get_paraswap_quote(WETH, USDC, weth_out, 18, 6)
usdc_back = int(route2['destAmount'])
print(f'  -> {usdc_back/1e6:.4f} USDC')

# Calculate profit
premium = amount_usdc * 5 // 10000  # 0.05% flash loan fee
repay = amount_usdc + premium
profit = usdc_back - repay

print(f'\n📊 ARB ANALYSIS:')
print(f'  Borrow:   ${amount_usdc/1e6:.2f}')
print(f'  Repay:    ${repay/1e6:.2f} (+0.05% fee)')
print(f'  Get back: ${usdc_back/1e6:.4f}')
print(f'  Profit:   ${profit/1e6:.4f}')

if profit <= 0:
    print('\n❌ No profit — market gak ada spread cukup')
    sys.exit(1)

# Get tx data for the FIRST swap (USDC -> WETH)
tx1 = get_paraswap_tx(route1, USDC, WETH, amount_usdc, route1['destAmount'])
print(f'\nParaSwap target: {tx1["to"]}')
print(f'Gas: {tx1.get("gas", "?")}')

# Deploy contract first? Or use existing?
print('\n⚠️ Contract belum di-deploy. Deploy dulu:')
print('   cd ~/.hermes/bozagentic-v7/flash-arb')
print('   forge create src/FlashLoanArbParaSwap.sol:FlashLoanArbParaSwap \\')
print('     --rpc-url https://base-rpc.publicnode.com \\')
print('     --private-key <PK> --legacy --broadcast')
print()
print('Kemudian execute:')
print(f'   contract.execute(amount, target, data, value)')
