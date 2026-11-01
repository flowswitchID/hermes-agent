# Broken Authentication

## Overview
Authentication mechanisms fail to correctly verify user identity.

## Risk
Account compromise and unauthorized access.

## Common Root Causes
- Weak credential validation
- Predictable authentication flow
- Missing rate limiting
- Insecure session creation

## Recon Indicators
- Multiple login endpoints
- Legacy authentication
- Debug authentication APIs

## Discovery Strategy
Review authentication flow, token issuance, session lifecycle, and edge cases.

## AI Reasoning Checklist
- Can identity be bypassed?
- Can credentials be brute forced?
- Is session bound to the correct user?

## False Positive Indicators
Expected login failures or intentionally anonymous endpoints.

## Business Impact
Unauthorized account access.

## Related
OWASP A07 / CWE-287
