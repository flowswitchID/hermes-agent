# SQL Injection

## Overview
User-controlled input influences SQL queries.

## Root Causes
- Dynamic query construction
- Missing parameterization

## Recon Indicators
- Search
- Filters
- Login
- Reporting

## Discovery Strategy
Identify query sinks and verify parameter handling.

## AI Reasoning Checklist
- Is input concatenated?
- Are prepared statements used?
- Can query structure change?

## Business Impact
Data disclosure, modification, authentication bypass.

## Related
CWE-89 / OWASP A03
