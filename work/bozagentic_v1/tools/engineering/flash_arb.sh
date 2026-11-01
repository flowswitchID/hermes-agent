#!/bin/bash
# BOZAGENTIC — Flash Loan Arb (single shot)
# Usage: bash flash_arb.sh

export PATH="$HOME/.foundry/bin:$PATH"
RPC="https://base.gateway.tenderly.co"
PK="PK_REDACTED_USE_ENV_VAR"
W="0xWALLET_ADDR_REDACTED"
C="0xcb135B9E2091301dc331f30CF0EeD82fCe187e27"

# 1. Send USDC to contract for balance check
USDC_BAL=$(cast call 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 "balanceOf(address)(uint256)" $W --rpc-url $RPC)
echo "USDC in wallet: $(echo $USDC_BAL | awk '{print $1/1e6}')"

echo "Sending USDC to contract..."
cast send 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 "transfer(address,uint256)" $C $USDC_BAL \
  --rpc-url $RPC --private-key $PK --legacy 2>&1 | grep -E "transactionHash|Error"

echo ""
echo "Contract USDC: $(cast call 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 "balanceOf(address)(uint256)" $C --rpc-url $RPC | awk '{print $1/1e6}')"
echo "Contract WETH: $(cast call 0x4200000000000000000000000000000000000006 "balanceOf(address)(uint256)" $C --rpc-url $RPC | awk '{print $1/1e18}')"
echo "Wallet ETH: $(cast balance $W --rpc-url $RPC | awk '{print $1/1e18}')"
