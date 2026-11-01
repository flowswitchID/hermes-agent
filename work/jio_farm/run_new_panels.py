#!/usr/bin/env python3
"""Run Jio Gemini farm flow restricted to the 2 new live panels."""
import sys
sys.path.insert(0, "/root/jio_farm")
import myjio

myjio.FIREBASE_PANELS = [
    ("https://jackie-7a125-default-rtdb.firebaseio.com", ""),
    ("https://vicky-singh-20bdd-default-rtdb.firebaseio.com", ""),
]

if __name__ == "__main__":
    raise SystemExit(myjio.main())
