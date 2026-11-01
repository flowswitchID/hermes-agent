#!/usr/bin/env python3
"""Deep decode Universal Router execute() call"""
import json, urllib.request
from eth_abi import decode

R = 'https://base-rpc.publicnode.com'
TX = '0x5fe36d72c3768f28e3bf727990a8763f71e41f626a8b4c8509c5b41525da6743'

tx_data = json.loads(urllib.request.urlopen(urllib.request.Request(R, data=json.dumps({'jsonrpc':'2.0','method':'eth_getTransactionByHash','params':[TX],'id':1}).encode(), headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'}),timeout=15).read())['result']
raw = bytes.fromhex(tx_data['input'][2:])
val = int(tx_data['value'], 16)

print(f'=== FULL DECODE ===')
print(f'Selector: {"0x" + raw[:4].hex()}')
print(f'Value: {val} wei ({val/1e18:.10f} ETH)')
print()

# Parse the ABI: (bytes commands, bytes[] inputs, uint256 deadline)
# offset + offset + uint256 = 96 bytes overhead
encoded = raw[4:]

# Decode top level
commands_offset = int.from_bytes(encoded[0:32], 'big')
inputs_offset = int.from_bytes(encoded[32:64], 'big')
deadline = int.from_bytes(encoded[64:96], 'big')

print(f'Commands offset: {commands_offset}')
print(f'Inputs offset: {inputs_offset}')
print(f'Deadline: {deadline}')
print()

# Parse commands
cmds_len = int.from_bytes(encoded[commands_offset:commands_offset+32], 'big')
commands = encoded[commands_offset+32:commands_offset+32+cmds_len]
print(f'Commands ({cmds_len} bytes): {commands.hex()}')
print(f'Commands as hex array: {[hex(c) for c in commands]}')
print()

# Parse inputs array
inputs_len = int.from_bytes(encoded[inputs_offset:inputs_offset+32], 'big')
print(f'Inputs count: {inputs_len}')

for i in range(inputs_len):
    cmd = commands[i]
    # Each input offset is at inputs_offset + 32 + i*32
    elem_offset = int.from_bytes(encoded[inputs_offset+32+i*32:inputs_offset+64+i*32], 'big')
    abs_start = inputs_offset + elem_offset
    elem_len = int.from_bytes(encoded[abs_start:abs_start+32], 'big')
    elem_data = encoded[abs_start+32:abs_start+32+elem_len]
    
    print(f'\n--- Input {i} (command 0x{cmd:02x}) — {elem_len} bytes ---')
    print(f'  Raw hex: {elem_data.hex()[:120]}')
    
    if cmd == 0x0b:  # V3_SWAP_EXACT_IN — try decode
        try:
            # Maybe the format is different: (uint256, bytes) for a path selector
            d = decode(['uint256', 'bytes'], elem_data)
            print(f'  Decoded as (uint256, bytes):')
            print(f'    Amount: {d[0]}')
            print(f'    Bytes: {d[1].hex()[:80]}')
        except:
            try:
                d = decode(['uint256', 'uint256', 'uint256', 'bytes'], elem_data)
                print(f'  Decoded as (uint256,uint256,uint256,bytes):')
                print(f'    Vals: {d[:3]}')
                print(f'    Bytes: {d[3].hex()[:80]}')
            except:
                print(f'  Could not decode with standard formats')
    
    elif cmd == 0x10:  # Sweep
        try:
            d = decode(['address', 'address', 'uint256'], elem_data)
            print(f'  Decoded as (address,address,uint256):')
            print(f'    token: {d[0]}')
            print(f'    recipient: {d[1]}')
            print(f'    amountMin: {d[2]}')
        except:
            print(f'  Could not decode sweep format')
    
    elif cmd == 0x0c:  # Unwrap
        try:
            d = decode(['address', 'uint256'], elem_data)
            print(f'  Decoded as (address,uint256):')
            print(f'    recipient: {d[0]}')
            print(f'    amountMin: {d[1]}')
        except:
            print(f'  Could not decode unwrap format')
PY