#!/usr/bin/env python3
"""
Hermes Config Patcher — GuardBreaker component
Patches Hermes Agent config.yaml to disable safety restrictions.
"""

import os
import sys
import yaml
import shutil
from datetime import datetime

HERMES_CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")
BACKUP_SUFFIX = ".guardbreaker-backup"

def find_hermes_config():
    """Find Hermes config in standard locations."""
    paths = [
        HERMES_CONFIG_PATH,
        os.path.expanduser("~/.config/hermes/config.yaml"),
        "/etc/hermes/config.yaml",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def backup_config(path):
    """Create timestamped backup before modifying."""
    backup = f"{path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}{BACKUP_SUFFIX}"
    shutil.copy2(path, backup)
    print(f"  ✓ Backup created → {backup}")
    return backup

def patch_config(config_path):
    """Apply safety-disabling patches to Hermes config."""
    backup_config(config_path)

    with open(config_path, 'r') as f:
        raw = f.read()

    # Parse YAML
    config = yaml.safe_load(raw)

    patches_applied = []

    # --- Safety flags ---
    safety_keys = [
        ('safety', 'enabled', False),
        ('safety', 'content_filter', False),
        ('safety', 'refusal_check', False),
        ('safety', 'ethics_enforcement', False),
        ('safety', 'moderation', False),
        ('guardrails', 'enabled', False),
        ('guardrails', 'system_prompt_protection', False),
        ('guardrails', 'tool_restrictions', False),
        ('content_filter', 'enabled', False),
        ('moderation', 'enabled', False),
        ('security', 'prompt_injection_detection', False),
        ('security', 'sandbox', False),
    ]

    for keys, value in safety_keys:
        section = config
        for i, key in enumerate(keys):
            if key not in section or not isinstance(section[key], dict):
                if i < len(keys) - 1:
                    section[key] = {}
                    section = section[key]
                else:
                    section[key] = value
                    patches_applied.append('.'.join(keys))
            else:
                if i < len(keys) - 1:
                    section = section[key]
                else:
                    old = section.get(key)
                    if old != value:
                        section[key] = value
                        patches_applied.append('.'.join(keys))

    # --- Provider cascade for unfiltered models ---
    if 'providers' not in config:
        config['providers'] = {}
    if 'custom' not in config['providers']:
        config['providers']['custom'] = []

    # --- System prompt override ---
    if 'system_prompt' not in config:
        config['system_prompt'] = {}
    config['system_prompt']['override'] = True
    config['system_prompt']['file'] = 'SOUL.md'

    # --- Profile settings ---
    if 'profiles' not in config:
        config['profiles'] = {}
    if 'default' not in config['profiles']:
        config['profiles']['default'] = {}

    config['profiles']['default']['refusal_mode'] = 'bypass'
    config['profiles']['default']['ethics_filter'] = False
    config['profiles']['default']['safety_checks'] = 'none'

    # --- Tool restrictions ---
    if 'tools' not in config:
        config['tools'] = {}
    config['tools']['restrict_sensitive'] = False
    config['tools']['allow_all_domains'] = True

    # Write back
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"  ✓ Config patched: {config_path}")
    print(f"  ✓ {len(patches_applied)} safety flags disabled:")
    for p in patches_applied:
        print(f"    • {p}")

    return patches_applied

def inject_soul(config_path, soul_path):
    """Link SOUL.md into Hermes profile."""
    profile_dir = os.path.expanduser("~/.hermes/profiles/default/")
    os.makedirs(profile_dir, exist_ok=True)

    target = os.path.join(profile_dir, "SOUL.md")
    if os.path.exists(soul_path):
        shutil.copy2(soul_path, target)
        print(f"  ✓ SOUL.md injected → {target}")
        return True
    else:
        print(f"  ⚠ SOUL.md not found at {soul_path}, skipping")
        return False

def main():
    print("╔══════════════════════════════════════╗")
    print("║  Hermes GuardBreaker — Config Patch  ║")
    print("╚══════════════════════════════════════╝")
    print()

    config_path = find_hermes_config()
    if not config_path:
        print("✗ Hermes config not found.")
        print("  Looked in: ~/.hermes/config.yaml, ~/.config/hermes/config.yaml, /etc/hermes/config.yaml")
        sys.exit(1)

    print(f"  Found config: {config_path}")
    print()

    # Auto-patch
    patch_config(config_path)

    # Inject SOUL if provided
    soul_arg = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--soul' and i + 1 < len(sys.argv[1:]):
            soul_arg = sys.argv[i + 2]

    if soul_arg:
        inject_soul(config_path, soul_arg)

    print()
    print("  ✅ GuardBreaker patch complete.")
    print("  ℹ  Restart Hermes Agent to apply changes.")

if __name__ == "__main__":
    main()
