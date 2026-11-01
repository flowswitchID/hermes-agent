# #27: Bypassing Validation for Nested MsgEthereumTx in MsgExec
Labels: ['bug', '3 (High Risk)', 'primary issue', 'sponsor confirmed', 'sufficient quality report', 'unsatisfactory', ':robot:_primary']
Accepted: True

In the file [authz_guard.go](https://github.com/code-423n4/2024-11-nibiru/blob/main/app/ante/authz_guard.go#L56), the AnteHandle function prohibits MsgEthereumTx messages within the execution messages of authz.MsgExec.

However, the current implementation only iterates over the top-level messages in msgExec and checks their types for MsgEthereumTx. It does not recursively inspect nested MsgExec structures, such as a msgExec containing another msgExec that encapsulates MsgEthereumTx.

```go
// Also rejects authz exec tx.json with any MsgEthereumTx inside
func (rmd AnteDecoratorAuthzGuard) AnteHandle(
	ctx sdk.Context, tx sdk.Tx, simulate bool, next sdk.AnteHandler,
) (newCtx sdk.Context, err error) {
	for _, msg := range tx.GetMsgs() {
		...
		// Also reject MsgEthereumTx in exec
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

### Proof of Concept

The current implementation only checks the first level of messages in authz.MsgExec. If an attacker creates a nested structure, it can bypass validation for MsgEthereumTx:

```go
Outer MsgExec:
  - Inner MsgExec:
      - MsgEthereumTx
```

By constructing such a structure, the AnteHandle validation can be bypassed, allowing a malicious MsgEthereumTx to pass undetected.

**Start the Node:**

**Initialize the Blockchain Node**

- Initialize the blockchain node and create necessary configuration files (e.g., config.toml, genesis.json) for the new blockchain.
- Set the validator's node name (gxh191) and the chain ID (nibiru-1).

Initialize the environment and specify the identity of the node and the blockchain it participates in.

```go
nibid init gxh191 --chain-id nibiru-1
```

**Create Validator Account**

- Create a local key pair to manage the validator's account.
- Generate a mnemonic and address to register the account on the blockchain.

Configure the validator's account to enable signing transactions and operations.

```go
nibid keys add validator
```

```go
- address: nibi16jvwx57mhn6yv96egyd7g2mjw2wu4s93tmkg3k
  name: validator
  pubkey: '{"@type":"/cosmos.crypto.secp256k1.PubKey","key":"AsnVfrZbG3Hr+wDgtcjDOuBFqJpVJ/9q3bAH1CThECM4"}'
  type: local
```

**Set Validator Account as Super Admin**

- Set the validator account as a sudo root account to manage blockchain permissions.

```go
nibid genesis add-sudo-root-account nibi16jvwx57mhn6yv96egyd7g2mjw2wu4s93tmkg3k
```

**Allocate Initial Funds to Validator Account**

- Allocate 1000 UNIBI tokens to the validator account.

Fund the account to enable subsequent operations, such as creating a validator and paying transaction fees.

```go
nibid genesis add-genesis-account nibi16jvwx57mhn6yv96egyd7g2mjw2wu4s93tmkg3k 1000000000unibi
```

**Generate Validator Transaction**

- Generate a genesis transaction for the validator and commit its self-delegated funds.

Register the validator to enable participation in blockchain consensus.

```go
nibid genesis gentx validator 100000000unibi --chain-id nibiru-1
```

**Collect and Update Genesis File**

- Merge the validator's genesis transaction into the genesis.json file. Ensure that the validator node information is recorded in the genesis file.

```go
nibid genesis collect-gentxs
```

**Validate Genesis File**

- Verify that the genesis.json file is properly formatted to ensure the chain can start successfully. This prevents configuration errors that could cause the chain to fail.

```go
nibid genesis validate-genesis
```

**Start the Node**

```go
nibid start
```

At this point, the node is up and running, and further exploitation can begin:

---

**Create a New Delegator Account**

- Create another local account (grantee) to simulate a malicious user or delegator account.

```go
nibid keys add grantee
```

```go
- address: nibi1l2jst6t2dn8dxd079xyxfsgra0ffeyck2qa8u2
  name: grantee
  pubkey: '{"@type":"/cosmos.crypto.secp256k1.PubKey","key":"A2x481ny7OZWsDln7zw07SIWwB05dXuVTkr34qsQapuy"}'
  type: local
```

**Transfer Funds to Delegator Account**

- Transfer 500 UNIBI to the grantee account. This provides funds to execute subsequent operations.

```go
nibid tx bank send nibi16jvwx57mhn6yv96egyd7g2mjw2wu4s93tmkg3k nibi1l2jst6t2dn8dxd079xyxfsgra0ffeyck2qa8u2 500000000unibi \
  --chain-id=nibiru-1 \
  --fees=500unibi
```

---

**Execute Authorization with MsgExec**

```go
nibid tx authz exec msg_exec.json --from nibi1l2jst6t2dn8dxd079xyxfsgra0ffeyck2qa8u2 --chain-id=nibiru-1 --fees=500unibi
```

**Example msg_exec.json**

You can refer to this structure: [Bypassing Ethermint Ante Handlers](https://jumpcrypto.com/writing/bypassing-ethermint-ante-handlers/).

```go
Outer MsgExec:
  - Inner MsgExec:
      - MsgEthereumTx
```

### Recommended Fix

To address this vulnerability, implement recursive checks for MsgExec messages and limit the maximum depth of nested structures to prevent potential DoS attacks.

```go
func (rmd AnteDecoratorAuthzGuard) AnteHandle(
	ctx sdk.Context, tx sdk.Tx, simulate bool, next sdk.AnteHandler,
) (newCtx sdk.Context, err error) {
	maxNestedMsgs := 5 // Set maximum nesting depth

	for _, msg := range tx.GetMsgs() {
		// Check for nested MsgExec with recursive validation
		if msgExec, ok := msg.(*authz.MsgExec); ok {
			if err := rmd.checkMsgExecRecursively(msgExec, 0, maxNestedMsgs); err != nil {
				return ctx, errors.Wrapf(
					errortypes.ErrInvalidType,
					err.Error(),
				)
			}
		}
	}

	return next(ctx, tx, simulate)
}

func (rmd AnteDecoratorAuthzGuard) checkMsgExecRecursively(msgExec *authz.MsgExec, depth int, maxDepth int) error {
	if depth >= maxDepth {
		return fmt.Errorf("exceeded max nested message depth: %d", maxDepth)
	}

	msgsInExec, err := msgExec.GetMessages()
	if err != nil {
		return errors.Wrapf(
			errortypes.ErrInvalidType,
			"failed getting exec messages %s", err,
		)
	}

	for _, msg := range msgsInExec {
		if _, ok := msg.(*evm.MsgEthereumTx); ok {
			return fmt.Errorf("MsgEthereumTx is not allowed")
		}
		if nestedExec, ok := msg.(*authz.MsgExec); ok {
			if err := rmd.checkMsgExecRecursively(nestedExec, depth+1, maxDepth); err != nil {
				return err
			}
		}
	}

	return nil
}
```

This fix ensures that nested structures are thoroughly validated, preventing unauthorized MsgEthereumTx execution.