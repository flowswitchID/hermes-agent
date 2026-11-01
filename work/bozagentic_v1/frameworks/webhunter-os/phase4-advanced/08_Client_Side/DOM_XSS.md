# DOM-based XSS

## Overview
Client-side JavaScript processes untrusted input and writes it into dangerous DOM sinks.

## AI Reasoning Checklist
- Does user input reach innerHTML, eval, or document.write?
- Is sanitization applied consistently?

## Related
CWE-79
