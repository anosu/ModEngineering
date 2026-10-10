import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import android_artifacts


class AndroidArtifactTests(unittest.TestCase):
    def test_detects_changed_added_removed_sources_and_modified_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "build_android.py").write_text("build")
            source = root / "android/src/Helper.java"
            binary = root / "android/build/classes.dex"
            source.parent.mkdir(parents=True)
            binary.parent.mkdir(parents=True)
            source.write_text("source")
            binary.write_bytes(b"dex")
            android_artifacts.write(root)
            android_artifacts.verify(root)
            for file, content in [(source, b"changed"), (binary, b"changed"), (source.with_name("New.java"), b"new")]:
                with self.subTest(file=file):
                    original = file.read_bytes() if file.exists() else None
                    file.write_bytes(content)
                    with self.assertRaisesRegex(ValueError, "Stale"):
                        android_artifacts.verify(root)
                    if original is None:
                        file.unlink()
                    else:
                        file.write_bytes(original)
            source.unlink()
            with self.assertRaisesRegex(ValueError, "Stale"):
                android_artifacts.verify(root)

    def test_missing_manifest_or_native_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "rebuild"):
                android_artifacts.verify(root)
            (root / "android/native").mkdir(parents=True)
            (root / "android/native/bridge.c").write_text("native")
            with self.assertRaisesRegex(ValueError, "JNI binary"):
                android_artifacts.snapshot(root)
