# Session Fixation

## Overview
An attacker forces or predicts a victim's session identifier before authentication.

## Root Causes
- Session ID not regenerated after login
- Predictable session identifiers

## Recon Indicators
- Session persists across authentication
- Static session identifiers

## Discovery Strategy
Compare session identifiers before and after login/logout.

## AI Reasoning Checklist
- Is the session regenerated after authentication?
- Can a fixed session be reused?

## Related
CWE-384
