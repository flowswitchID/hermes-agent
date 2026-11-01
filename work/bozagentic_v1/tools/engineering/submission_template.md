## Summary
Fee calculation allows operator fee to exceed global fee due to rounding

## Severity
Medium — 55/100

## Affected Component
- Contract: 
- Function: 
- Line: 450

## Description
The operator fee is calculated as a percentage of the global fee. Due to integer division rounding, in edge cases the operator fee can exceed the intended proportion.

## Impact
Operators receive slightly more fees than intended, reducing withdrawer returns.

## Proof of Concept


## Recommended Fix


## References
Z3 proof: P4 operator<=global verified UNSAT for normal ranges
