#!/usr/bin/env python3
"""UniV3 Arbitrage Scanner - checks every scan, auto-executes when profitable."""
import subprocess, time

RPC = 'https://base.gateway.tenderly.co'
W = '0xWALLET_ADDR_REDACTED'
PK = 'PK_REDACTED_USE_ENV_VAR'
C = '0xA8cF3d29E68F96eF129eC917F8eF231bd5f439DA'  # FinalArb

POOLS = {
    '1.00%': ('0x0b1c2dcbbfa744ebd3fc17ff1a96a1e1eb4b2d69', 1.00),
    '0.30%': ('0x6c561B446416E1A00E8E93E221854d6eA4171372', 0.30),
    '0.05%': ('0xd0b53D9277642d899DF5C87A3966A349A798F224', 0.05),
    '0.01%': ('0xb4cb800910b228ed3d0834cf79d697127bbb00e5', 0.01),
}

while True:
    prices = {}
    for name, (addr, fee) in POOLS.items():
        r = subprocess.run(['cast','call',addr,'slot0()(uint160)','--rpc-url',RPC],
            capture_output=True, text=True, timeout=10)
        sqrt = int(r.stdout.strip().split()[0].split('[')[0])
        prices[name] = (sqrt / 2**96) ** 2 * 1e12
    
    best_net = -999
    best_buy = best_sell = ''
    
    names = list(POOLS.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            n1, n2 = names[i], names[j]
            p1, p2 = prices[n1], prices[n2]
            spread = abs(p1 - p2) / min(p1, p2) * 100
            total_fee = POOLS[n1][1] + POOLS[n2][1]
            net = spread - total_fee
            if net > best_net:
                best_net = net
                best_buy, best_sell = (n1, n2) if p1 < p2 else (n2, n1)
    
    now = time.strftime('%H:%M:%S')
    if best_net > 0:
        print(f'[{now}] ⚡ ARB! {best_buy}→{best_sell} net={best_net:.3f}%')
        amt = 500_000000  # $500 test
        try:
            r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',PK,
                '--legacy','--gas-limit','400000', C, 'execute(uint256)', str(amt)],
                capture_output=True, text=True, timeout=120)
            if '"status":"0x1"' in r.stdout:
                print(f'  ✅ EXECUTED SUCCESSFULLY!')
                break
            else:
                print(f'  ❌ TX failed')
        except Exception as e:
            print(f'  ❌ Error: {e}')
    elif best_net > -0.5:
        print(f'[{now}] ⏳ Best: {best_buy}→{best_sell} net={best_net:.3f}% (too thin)')
    else:
        print(f'[{now}] ⏳ No arb (best net={best_net:.3f}%)')
    
    time.sleep(60)  # check every 60 seconds
