import re, json, urllib.request

# Read bytecode directly
import subprocess
r = subprocess.run(['cast', 'code', '0x0F7Ae28dE1C8532170AD4ee566B5801485c13a0E',
    '--rpc-url', 'https://base.gateway.tenderly.co'],
    capture_output=True, text=True, timeout=15)
code = r.stdout.strip()
print(f"Bytecode length: {len(code)} chars ({len(code)//2} bytes)")
print(f"Active: {len(code) > 100}")

bc = code[2:] if code.startswith('0x') else code

# Find PUSH4 + selector patterns
selectors = set()
for m in re.finditer(r'63([0-9a-f]{8})', bc):
    sel = '0x' + m.group(1)
    try:
        val = int(sel, 16)
        if val >= 0x01000000 and val <= 0xffffffff:
            selectors.add(sel)
    except:
        pass

print(f"\nSelectors found: {len(selectors)}")
for s in sorted(selectors)[:15]:
    try:
        url = f'https://api.4byte.directory/api/v1/signatures/?hex_signature={s[2:]}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        results = data.get('results', [])
        if results:
            print(f"  {s} -> {results[0]['text_signature']}")
        else:
            print(f"  {s} -> (unknown)")
    except:
        print(f"  {s} -> (error)")

# Check bytecode for known patterns
checks = [
    ('transferFrom', '23b872dd'),
    ('approve', '095ea7b3'),
    ('selfdestruct', '43ff'),
    ('call', 'f1'),  # CALL opcode
    ('staticcall', 'fa'),  # STATICCALL
    ('revert', 'fd'),  # REVERT
]
print(f"\nOpcodes:")
for name, sig in checks:
    found = sig in bc.lower()
    print(f"  {'✅' if found else '❌'} {name} ({sig})")
