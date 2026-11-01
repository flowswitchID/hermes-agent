# MEDUSA MASTER — Coverage-Guided Fuzzing Reference
# BOZAGENTIC | Config, assertion testing, coverage

---

## BASICS

```bash
# Run with config
medusa fuzz --config medusa.json

# Quick run (no config)
medusa fuzz
```

## CONFIG (medusa.json)

```json
{
  "fuzzing": {
    "workers": 4,
    "testLimit": 50000,
    "callSequenceLength": 10,
    "corpusDirectory": "corpus",
    "coverageEnabled": true,
    "targetContracts": ["MyContract"],
    "deployerAddress": "0x30000",
    "senderAddresses": ["0x30000", "0x40000"],
    "testing": {
      "stopOnFailedTest": false,
      "stopOnNoTests": true,
      "assertionTesting": {
        "enabled": true,
        "testViewMethods": true,
        "assertionTypes": [
          "IntegerOverflow",
          "InvalidEnumAccess",
          "InvalidMemoryAccess",
          "OutOfBoundsIndexAccess"
        ]
      },
      "propertyTesting": {
        "enabled": true,
        "testPrefixes": ["echidna_"]
      }
    }
  },
  "compilation": {
    "platform": "crytic-compile",
    "platformConfig": {"target": "."}
  }
}
```

## KEY DIFFERENCES FROM ECHIDNA

```
FEATURE          | ECHIDNA              | MEDUSA
═════════════════|══════════════════════|══════════════════════
Language         | Haskell              | Go
Coverage         | Basic                | Advanced (lcov, html)
Assertion types  | All assert()         | Configurable types
Property prefix  | echidna_             | echidna_ (compatible)
Corpus           | Yes                  | Yes
Shrinking        | Yes                  | Yes
Multi-sender     | Yes                  | Yes
Cheatcodes       | Limited              | Foundry compatible
Slither integ.   | Via crytic-compile   | Built-in
```

## ASSERTION TYPES

```
IntegerOverflow:      Arithmetic overflow/underflow
InvalidEnumAccess:    Invalid enum value
InvalidMemoryAccess:  Out-of-bounds memory
CallWithTooLittleGas: Gas too low for call
InvalidBytesArrayLength: Bad bytes length
OutOfBoundsIndexAccess: Array index out of bounds
```

## RESULTS FROM COINBASE AUDIT

```
TEST                    | RUNS   | RESULT
════════════════════════|════════|══════════
BuilderCodes (assertion) | 100K  | 48/48 PASS ✅
BuilderCodes (4 senders) | 50K   | 48/48 PASS ✅
```

## LEVEL ASSESSMENT

```
BEFORE: 60% (basic config, trial-error)
NOW:    78% (multi-sender, coverage, assertion types)
EXPERT: 90% (custom providers, chain manipulation)
GAP:    custom value providers, advanced chain config
```
