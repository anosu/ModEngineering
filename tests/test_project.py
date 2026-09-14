import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import project


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        source = self.root / "src/Example"
        source.mkdir(parents=True)
        targets = Path(__file__).resolve().parents[1] / "build/Mod.targets"
        (source / "Example.csproj").write_text(
            f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Version>1.2.3</Version>
    <ModPlatform>android</ModPlatform>
  </PropertyGroup>
  <Target Name="ExtraFiles" BeforeTargets="GetModPackageFiles">
    <ItemGroup><ModPackageFile Include="$(MSBuildProjectDirectory)/font" Destination="UserData/Example/font" /></ItemGroup>
  </Target>
  <Import Project="{targets.as_posix()}" />
</Project>''',
            encoding="utf-8",
        )
        (source / "font").write_bytes(b"font-data")

    def test_discovers_project_and_new_tests_without_registration(self):
        test = self.root / "tests/Nested/Example.Tests/Example.Tests.csproj"
        test.parent.mkdir(parents=True)
        test.write_text("<Project />")
        project.solution(self.root)
        paths = [
            p.attrib["Path"] for p in ET.parse(self.root / (self.root.name + ".slnx")).getroot()
        ]
        self.assertIn("src/Example/Example.csproj", paths)
        self.assertIn("tests/Nested/Example.Tests/Example.Tests.csproj", paths)

    def test_package_uses_evaluated_msbuild_items_and_project_version(self):
        values = project.evaluate(self.root)["Properties"]
        output = Path(values["TargetDir"])
        output.mkdir(parents=True)
        (output / "Example.dll").write_bytes(b"compiled-mod")
        (output / "Utility.dll").write_bytes(b"compiled-library")
        with patch.object(project, "build"):
            archive = project.package(self.root, "Release", "v1.2.3")
        self.assertEqual("Example-Android.zip", archive.name)
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(
                {"Mods/Example/Example.dll", "Mods/Example/Utility.dll", "UserData/Example/font"},
                set(package.namelist()),
            )
            self.assertEqual(b"compiled-mod", package.read("Mods/Example/Example.dll"))
            self.assertEqual(b"font-data", package.read("UserData/Example/font"))
        self.assertTrue((archive.parent / "SHA256SUMS.txt").exists())

    def test_wrong_version_rejected_before_build_or_publication(self):
        with patch.object(project, "build") as build:
            with self.assertRaisesRegex(ValueError, "does not match"):
                project.package(self.root, "Release", "v2.0.0")
            build.assert_not_called()

    def test_paths_outside_output_are_rejected(self):
        with self.assertRaises(ValueError):
            project.contained(self.root, "../escape")

    def test_metadata_comes_from_project_not_a_manifest(self):
        (self.root / "unrelated.json").write_text(json.dumps({"Version": "99"}))
        self.assertEqual("1.2.3", project.evaluate(self.root)["Properties"]["Version"])


if __name__ == "__main__":
    unittest.main()
