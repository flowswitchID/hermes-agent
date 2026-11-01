"""
tools/engineering/sync_platforms.py
BOZAGENTIC Framework — Cross-Platform Rule & Identity Synchronizer
Automatically propagates SOUL.md rules to CLAUDE.md, .cursorrules, .clinerules, and openclaw.
"""

import os
import shutil

PROJ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SOUL_PATH = os.path.join(PROJ_ROOT, "SOUL.md")

TARGET_FILES = [
    os.path.join(PROJ_ROOT, "CLAUDE.md"),
    os.path.join(PROJ_ROOT, ".cursorrules"),
    os.path.join(PROJ_ROOT, ".clinerules"),
    os.path.join(PROJ_ROOT, "openclaw", "SOUL.md")
]

def sync_all():
    if not os.path.exists(SOUL_PATH):
        raise FileNotFoundError(f"Source SOUL.md not found at {SOUL_PATH}")

    with open(SOUL_PATH, "r", encoding="utf-8") as f:
        soul_content = f.read()

    synced = []
    for target in TARGET_FILES:
        target_dir = os.path.dirname(target)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(soul_content)
        synced.append(target)

    return synced

if __name__ == "__main__":
    res = sync_all()
    print(f"Successfully synced SOUL.md to {len(res)} platform targets:")
    for path in res:
        print(f"  ✓ {os.path.relpath(path, PROJ_ROOT)}")
