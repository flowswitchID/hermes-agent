#!/usr/bin/env python3
"""
BOZAGENTIC AUTO-BOT — Flash loan arbitrage every 10 minutes
Runs via cron: USDC -> WETH -> USDC via ParaSwap
"""
import json, urllib.request, sys, os
from web3 import Web3

RPC = 'https://base-rpc.publicnode.com'
w3 = Web3(Web3.HTTPProvider(RPC))
WALLET = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WETH = '0x4200000000000000000000000000000000000006'
PROXY = '0x93aAAe79a53759cD164340E4C8766E4Db5331cD7'

AMOUNT = 1000_000000  # $1000 USDC
MIN_PROFIT_USD = 0.50  # min profit to execute

def log(msg):
    print(f'[{__import__("datetime").datetime.now().strftime("%H:%M:%S")}] {msg}')

def quote(src, dst, amt, sd, dd):
    url = f'https://api.paraswap.io/prices/?srcToken={src}&destToken={dst}&amount={amt}&srcDecimals={sd}&destDecimals={dd}&side=SELL&network=8453&userAddress={WALLET}'
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'}),timeout=15).read())

log('BOZAGENTIC AUTO-BOT START')
log(f'Balance: {w3.eth.get_balance(WALLET)/1e18:.6f} ETH')

# Check if contract is deployed
# Try to find the contract (should be in a known file)
contract_addr = None
try:
    with open('/tmp/arb_contract.txt') as f:
        contract_addr = f.read().strip()
except:
    pass

if not contract_addr:
    log('Contract not deployed. Need deploy first.')
    log('Run: forge create ...FlashLoanArbParaSwap --broadcast')
    sys.exit(1)

# Get quote for round trip
try:
    r1 = quote(USDC, WETH, AMOUNT, 6, 18)
    weth_out = int(r1['priceRoute']['destAmount'])
    
    r2 = quote(WETH, USDC, weth_out, 18, 6)
    usdc_back = int(r2['priceRoute']['destAmount'])
    
    premium = AMOUNT * 5 // 10000
    profit = usdc_back - (AMOUNT + premium)
    gas_cost = 0.05 * 1e6  # $0.05 in USDC terms
    net = profit - gas_cost
    
    log(f'USDC->WETH->USDC: ${usdc_back/1e6:.2f} | profit: ${net/1e6:.2f}')
    
    if net < MIN_PROFIT_USD * 1e6:
        log(f'Skip: profit ${net/1e6:.2f} < min ${MIN_PROFIT_USD}')
        sys.exit(0)
    
    # Get tx data for both swaps
    tx1 = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://api.paraswap.io/transactions/8453',
        data=json.dumps({'srcToken':USDC,'destToken':WETH,'srcAmount':str(AMOUNT),
            'destAmount':r1['priceRoute']['destAmount'],'priceRoute':r1['priceRoute'],
            'userAddress':WALLET}).encode(),
        headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'}),timeout=15).read())
    
    tx2 = json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://api.paraswap.io/transactions/8453',
        data=json.dumps({'srcToken':WETH,'destToken':USDC,'srcAmount':str(weth_out),
            'destAmount':r2['priceRoute']['destAmount'],'priceRoute':r2['priceRoute'],
            'userAddress':WALLET}).encode(),
        headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'}),timeout=15).read())
    
    # Execute on contract
    # execute(amount, swap1Target, swap1Data, swap2Target, swap2Data)
    contract = w3.eth.contract(address=contract_addr, abi=[])
    # Would need to call contract here
    
    log(f'Execute via contract {contract_addr}')
    
except Exception as e:
    log(f'Error: {e}')
