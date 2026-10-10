"""Check that embedded Android binaries match the sources last used to build them."""

import argparse
import hashlib
import json
from pathlib import Path


def snapshot(root: Path) -> dict:
    android = root / "android"
    sources = [root / "build_android.py"]
    for extension in ("*.java", "*.c", "*.h"):
        sources += sorted(p for p in android.rglob(extension) if "build" not in p.relative_to(android).parts)
    artifacts = [android / "build/classes.dex", *sorted((android / "build").rglob("*.so"))]
    if any(p.suffix == ".c" for p in sources) and len(artifacts) == 1:
        raise ValueError(f"Missing Android JNI binary in {root}")

    def hashes(files):
        return {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files
        }

    return {"sources": hashes(sources), "artifacts": hashes(artifacts)}


def write(root: Path) -> None:
    path = root / "android/build/manifest.json"
    path.write_text(json.dumps(snapshot(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify(root: Path) -> None:
    path = root / "android/build/manifest.json"
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))
        current = snapshot(root)
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot verify Android artifacts in {root}; rebuild with build_android.py: {error}") from error
    if recorded != current:
        raise ValueError(f"Stale Android artifacts in {root}; rebuild with build_android.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    verify(args.repo.resolve())
