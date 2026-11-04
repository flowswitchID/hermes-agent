---
name: number-extraction-regex
description: Extract Indian phone numbers from Firebase RTDB payloads.
---

# Phone Number Extraction Regex — Firebase RTDB

## Scope
Patterns for extracting Indian phone numbers (10-digit, 6-9xx leading) from Firebase RTDB message payloads harvested during panel scans.

## Field Coverage Order
1. `simInfo.phoneNumber`, `simInfo.number`, `simInfo.mobile`, `simInfo.contact`, `simInfo.msisdn`
2. Top-level: `phoneNumber`, `mobileNumber`, `number`, `contact`, `msisdn`, `phone`
3. Nested under: `device`, `data`, `payload` — repeat field names from (1) and (2)
4. Raw message body: fallback regex on entire JSON string

## Patterns
```python
# Structured fields with flexible nesting
r'(?i)(?:phoneNumber|mobileNumber|number|contact|msisdn|phone)[\"\']?\s*[:=]\s*[\"\']([6-9]\d{9})[\"\']'

# Raw body fallback — standalone 10-digit 6-9xx
r'(?<![\d])([6-9]\d{9})(?![\d])'

# SIM info nested
r'(?i)simInfo\s*[{:][^}]*?(?:phoneNumber|number|mobile|contact|msisdn)[\"\']?\s*[:=]\s*[\"\']([6-9]\d{9})[\"\']'
```

## Pitfalls
- Do not anchor with `^` or `$`; payloads are multiline JSON.
- Match both single and double quotes around values.
- Apply field-name regex first; if zero matches, fall back to raw body scan.
- Dedupe extracted numbers before OTP/activation step to avoid redundant requests.