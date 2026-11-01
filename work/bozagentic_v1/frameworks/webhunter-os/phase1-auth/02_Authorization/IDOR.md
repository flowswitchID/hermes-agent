# Insecure Direct Object Reference (IDOR)

## Overview
Object identifiers can be manipulated to access unauthorized resources.

## Recon Indicators
Sequential IDs, UUID exposure, predictable references.

## Discovery Strategy
Modify object identifiers across accounts and roles.

## AI Reasoning Checklist
- Is ownership validated?
- Does object access depend only on the identifier?

## Related
CWE-639
