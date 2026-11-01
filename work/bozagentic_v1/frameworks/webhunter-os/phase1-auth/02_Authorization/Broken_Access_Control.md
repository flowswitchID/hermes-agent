# Broken Access Control

## Overview
Users can access resources or functions beyond intended permissions.

## Discovery Strategy
Compare requests across roles and ownership boundaries.

## AI Reasoning Checklist
- Can another user's resource be accessed?
- Are admin endpoints protected?
- Is authorization enforced server-side?

## Business Impact
Privilege escalation and data exposure.

## Related
OWASP A01 / CWE-284
