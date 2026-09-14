import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mod import generated, solution, sync, within

spec = importlib.util.spec_from_file_location(
    "new_mod", Path(__file__).resolve().parents[1] / "scripts/new-mod.py"
)
new_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_mod)


class EngineeringTests(unittest.TestCase):
    def test_rejects_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                within(Path(directory), "../outside")

    def test_generated_configuration_detects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = new_mod.scaffold(
                root, "Example-Android", "Example", "android", "example/Example-Android"
            )
            sync(root, config)
            sync(root, config, check=True)
            (root / "global.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "global.json"):
                sync(root, config, check=True)

    def test_solutions_include_test_and_fixed_runtime_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = new_mod.scaffold(
                root, "Example-Android-Variant", "Example", "android", "example/Example-Android-Variant"
            )
            config.update(useExtension=True, tests=["tests/Example.Tests/Example.Tests.csproj"])
            solution(root, config)
            projects = [
                p.attrib["Path"] for p in ET.parse(root / "Example-Android-Variant.slnx").getroot()
            ]
            self.assertIn("shared/Extension/src/Extension/Extension.csproj", projects)
            self.assertIn("tests/Example.Tests/Example.Tests.csproj", projects)

    def test_android_template_preserves_package_contract_and_single_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = new_mod.scaffold(
                root, "Example-Android", "Example", "android", "example/Example-Android"
            )
            self.assertEqual(
                ["Mods/Example/Example.dll", "Mods/Example/Utility.dll"],
                [p["destination"] for p in config["package"]["files"]],
            )
            project = ET.parse(root / config["project"]).getroot()
            self.assertEqual("1.0.0", project.findtext("PropertyGroup/Version"))
            self.assertNotIn(
                "const string Version", (root / "src/Example/Core/ModInfo.cs").read_text()
            )

    def test_pc_template_has_explicit_deploy_and_no_android_package(self):
        with tempfile.TemporaryDirectory() as directory:
            config = new_mod.scaffold(
                Path(directory), "Example", "Example", "pc", "example/Example"
            )
            self.assertNotIn("package", config)
            self.assertIn("{configuration}", config["deployDirectory"])

    def test_consumer_workflow_pins_revision_and_passes_private_secret_only_when_needed(self):
        config = dict(
            repository="Example",
            project="src/Example/Example.csproj",
            kind="android",
            useExtension=False,
            engineeringRevision="a" * 40,
        )
        public = generated(config)[".github/workflows/build.yml"]
        self.assertIn("@" + "a" * 40, public)
        self.assertNotIn("DEPENDENCY_DEPLOY_KEY", public)
        config["useExtension"] = True
        self.assertIn("DEPENDENCY_DEPLOY_KEY", generated(config)[".github/workflows/build.yml"])


if __name__ == "__main__":
    unittest.main()
