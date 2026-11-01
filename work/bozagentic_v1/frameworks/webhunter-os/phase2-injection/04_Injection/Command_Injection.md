# Command Injection

## Overview
Application passes user input to operating system commands.

## Discovery Strategy
Locate OS command execution paths and validate input handling.

## AI Reasoning Checklist
- Does input reach shell execution?
- Are arguments escaped?
- Is a shell required?

## Related
CWE-78
