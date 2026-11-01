#!/usr/bin/env python3
"""Auto-generate accurate project metrics. Run: python3 tools/counts.py"""
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=root).stdout.strip()

# Total files (excluding __pycache__/ .pyc)
total_files = int(run("find . -type f -not -path '*/__pycache__/*' -not -name '*.pyc' | wc -l"))

# MD files
md_files = int(run("find . -type f -not -path '*/__pycache__/*' -name '*.md' | wc -l"))

# PY files
py_files = int(run("find . -type f -not -path '*/__pycache__/*' -name '*.py' | wc -l"))

# Total LOC (all source files) — computed live, never hardcoded
total_loc = int(run(
    r"find . -type f \( -name '*.py' -o -name '*.md' -o -name '*.json' "
    r"-o -name '*.toml' -o -name '*.txt' -o -name '*.sh' \) "
    r"-not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' "
    r"-exec cat {} + | wc -l"
))

# Skills count: every skill definition, independent of nesting depth.
skills_count = int(run("find skills -type f -name 'SKILL.md' | wc -l"))

# Tools count (all production Python files, excluding tests and package markers).
tools_count = int(run(
    "find tools -type f -name '*.py' -not -name '__init__.py' "
    "-not -path '*/tests/*' -not -name 'test_*.py' | wc -l"
))

# Test files
test_count = int(run(
    "find . -type f -not -path '*/__pycache__/*' -not -name '*.pyc' "
    r"\( -name 'test_*.py' -o -name '*_test.py' \) | wc -l"
))

# Directory size in KB
zip_size_kb = int(run("du -sk . | cut -f1"))

result = {
    "total_files": total_files,
    "md_files": md_files,
    "py_files": py_files,
    "total_loc": total_loc,
    "skills_count": skills_count,
    "tools_count": tools_count,
    "test_count": test_count,
    "zip_size_kb": zip_size_kb,
}

print(json.dumps(result, indent=2))
