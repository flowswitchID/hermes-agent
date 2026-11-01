import json, urllib.request
RPC = 'https://base-rpc.publicnode.com'

def w3_call(method, params=None):
    payload = json.dumps({'jsonrpc':'2.0','method':method,'params':params or [],'id':1}).encode()
    req = urllib.request.Request(RPC, data=payload, headers={'Content-Type':'application/json','User-Agent':'MEVbot/1.0'})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

block = w3_call('eth_getBlockByNumber', ['pending', True])
txs = block.get('result', {}).get('transactions', []) if block.get('result') else []
print(f'Pending txs: {len(txs)}')

UNI = '0xE592427A0AEce92De3Edee1F18E0157C05861564'.lower()
count = 0
for tx in txs:
    to = tx.get('to','')
    if to and to.lower() == UNI:
        inp = tx.get('input','')
        if inp and len(inp) > 10 and inp[2:10] == '414bf389':
            count += 1
            val = int(tx.get('value','0x0'), 16) / 1e18
            print(f'  Swap: {tx["from"][:10]}... ${val*1880:.0f}')
print(f'Uniswap V3 swaps: {count}')
