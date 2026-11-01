#!/usr/bin/env python3
"""
BOZAGENTIC — Manual Flash Loan Arb Executor
Pake pool Uniswap V3 langsung, gak perlu API.
"""
import subprocess, json, time
from web3 import Web3

W = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
RPC = 'https://base.gateway.tenderly.co'
w3 = Web3(Web3.HTTPProvider(RPC))

UNI_V3_POOLS = {
    '0.01%': '0xb4cb800910b228ed3d0834cf79d697127bbb00e5',
    '0.05%': '0xd0b53d9277642d899df5c87a3966a349a798f224',
    '0.30%': '0x6c561b446416e1a00e8e93e221854d6ea4171372',
    '1.00%': '0x0b1c2dcbbfa744ebd3fc17ff1a96a1e1eb4b2d69',
}

def get_price(pool):
    sqrt0 = subprocess.run(['cast','call',pool,'slot0()(uint160,uint24,uint16,uint16,uint16,uint8,bool)','--rpc-url',RPC], capture_output=True, text=True, timeout=10)
    sqrt = int(sqrt0.stdout.strip().split()[0]) if sqrt0.stdout.strip() else 0
    if sqrt > 0:
        return (sqrt / 2**96) ** 2 * 10**12
    return 0

# Scan pool prices
print(' SCAN HARGA POOL:')
for name, addr in sorted(UNI_V3_POOLS.items()):
    price = get_price(addr)
    print(f'  {name}: ${price:.2f}')

# Find best arb
prices = [(n, get_price(a), a) for n, a in UNI_V3_POOLS.items()]
for i in range(len(prices)):
    for j in range(i+1, len(prices)):
        n1, p1, a1 = prices[i]
        n2, p2, a2 = prices[j]
        if p1 > 0 and p2 > 0:
            spread = abs(p1-p2)/min(p1,p2)*100
            if spread > 0.05:
                side = 'BUY' if p1 < p2 else 'SELL'
                pool_buy = a1 if p1 < p2 else a2
                pool_sell = a2 if p1 < p2 else a1
                profit_1k = 1000 * spread / 100 - 0.5  # minus fee 0.05% + gas
                print(f'\n{n1} ${p1:.2f} vs {n2} ${p2:.2f} = {spread:.3f}%')
                print(f'  Beli di: {n1 if p1 < p2 else n2}')
                print(f'  Jual di: {n2 if p1 < p2 else n1}')
                print(f'  Profit $1k: ~${profit_1k:.2f}')
                if profit_1k > 0:
                    print(f'\n  ✅ LAYAK!')
                    print(f'  Deploy: forge create ManualFlashArb --rpc-url {RPC} --private-key <PK> --legacy --broadcast')
                    print(f'  Execute: cast send <contract> execute(1000000000, {pool_buy}, {pool_sell}) --rpc-url {RPC} --private-key <PK> --legacy')
