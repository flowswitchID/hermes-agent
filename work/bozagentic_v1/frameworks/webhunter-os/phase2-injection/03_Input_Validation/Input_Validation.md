# Input Validation

## Overview
Review how all untrusted input is validated before processing.

## Root Causes
- Missing validation
- Client-side only validation
- Inconsistent validation
- Trusting serialized input

## Recon Indicators
- Multiple input formats
- Rich text fields
- File metadata
- JSON/XML payloads

## Discovery Strategy
Trace input from entry point to sink and identify validation boundaries.

## AI Reasoning Checklist
- Is validation server-side?
- Are allowlists used?
- Are boundary cases handled?

## Related
CWE-20
