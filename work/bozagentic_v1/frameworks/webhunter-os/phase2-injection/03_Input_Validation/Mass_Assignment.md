# Mass Assignment

## Overview
Unexpected object properties modify protected server-side fields.

## Discovery Strategy
Compare accepted fields with documented schema and test extra attributes.

## AI Reasoning Checklist
- Are hidden fields accepted?
- Are sensitive properties writable?

## Related
CWE-915
