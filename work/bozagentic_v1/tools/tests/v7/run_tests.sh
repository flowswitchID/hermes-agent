#!/usr/bin/env bash
# Offline test suite for the top-level tools (Client Revenue Engine etc.).
# Zero external deps — pure stdlib unittest.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
export PYTHONPATH="$ROOT:$ROOT/tools:$ROOT/tools/engineering:$ROOT/tools/meta:$ROOT/tools/intelligence:$ROOT/tools/web3:$ROOT/tools/security:$ROOT/tools/team:$ROOT/tools/content:$ROOT/tools/monetization:$ROOT/tools/automation:${PYTHONPATH:-}"
cd "$HERE"
python3 -m unittest discover -p 'test_*.py' "$@"
