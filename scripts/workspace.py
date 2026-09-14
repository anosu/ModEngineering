"""Batch operations on an explicit inventory; never discovers arbitrary directories."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mod import DEFAULT_DEPENDENCY_KEY, extension_secret, load, update

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("command", choices=["upgrade", "extension-secret", "status"])
parser.add_argument(
    "--inventory",
    type=Path,
    required=True,
    help="JSON array of relative repository directory names",
)
parser.add_argument("--revision")
parser.add_argument(
    "--dependency", choices=["ModEngineering", "Utility", "Extension"], default="ModEngineering"
)
parser.add_argument("--key", type=Path, default=DEFAULT_DEPENDENCY_KEY)
args = parser.parse_args()
workspace = args.inventory.resolve().parent
failed = []
for name in json.loads(args.inventory.read_text(encoding="utf-8")):
    root = (workspace / name).resolve()
    if not root.is_relative_to(workspace):
        raise ValueError("Inventory path escaped workspace")
    config = load(root)
    try:
        if args.command == "upgrade":
            if not args.revision:
                parser.error("upgrade requires --revision")
            if (root / "shared" / args.dependency).exists():
                update(root, args.revision, args.dependency)
        elif args.command == "extension-secret":
            if not args.key:
                parser.error("extension-secret requires --key")
            if config.get("useExtension"):
                extension_secret(root, args.key)
        else:
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            print(name + "\n" + result.stdout)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        failed.append(name)
        print(f"{name}: {error}", file=sys.stderr)
if failed:
    sys.exit("Failed: " + ", ".join(failed))
