"""Build helpers using MSBuild configuration and normal directory conventions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath


def run(args: list[str], root: Path, *, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=root,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def project(root: Path) -> Path:
    projects = sorted(root.glob("src/*/*.csproj"))
    if len(projects) != 1:
        raise ValueError("Expected one application/library project under src/<name>/")
    return projects[0]


def tests(root: Path) -> list[Path]:
    return sorted(
        p for p in root.glob("tests/**/*.csproj") if not {"bin", "obj"}.intersection(p.parts)
    )


def evaluate(
    root: Path, configuration: str = "Release", *, package: bool = False, local: bool = False
) -> dict:
    args = [
        "dotnet",
        "msbuild",
        str(project(root)),
        "-nologo",
        "-verbosity:quiet",
        f"-p:Configuration={configuration}",
        "-getProperty:ModPlatform,Version,AssemblyName,TargetPath,TargetDir,GameDir,ModDeployDirectory,ModPackageName,UtilityProjectPath,ExtensionProjectPath",
    ]
    if not local:
        args.append("-p:UsePinnedSharedDependencies=true")
    if package:
        args += ["-target:GetModPackageFiles", "-getItem:ModPackageFile"]
    return json.loads(run(args, root, capture=True))


def solution(root: Path, local: bool = False) -> None:
    paths = [project(root), *tests(root)]
    values = evaluate(root, local=local)["Properties"]
    for name in ["UtilityProjectPath", "ExtensionProjectPath"]:
        if values[name]:
            dependency = Path(values[name]).resolve()
            if not dependency.is_file():
                raise ValueError(f"Missing project: {dependency}")
            paths.append(dependency)
    xml = ET.Element("Solution")
    for path in paths:
        ET.SubElement(xml, "Project", Path=os.path.relpath(path, root).replace("\\", "/"))
    ET.indent(xml, space="    ")
    target = root / (root.name + (".local" if local else "") + ".slnx")
    target.write_text(ET.tostring(xml, encoding="unicode") + "\n", encoding="utf-8")


def build(root: Path, configuration: str) -> None:
    run(
        [
            "dotnet",
            "build",
            str(project(root)),
            "-c",
            configuration,
            "-p:UsePinnedSharedDependencies=true",
            "--nologo",
        ],
        root,
    )


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes output directory: {relative}")
    return path


def package(root: Path, configuration: str, expected_version: str | None = None) -> Path:
    values = evaluate(root, configuration)["Properties"]
    if values["ModPlatform"] != "android":
        raise ValueError("Only Android projects have release packages")
    version = values["Version"]
    if expected_version and expected_version != "v" + version:
        raise ValueError(f"Tag {expected_version} does not match project version v{version}")
    build(root, configuration)
    data = evaluate(root, configuration, package=True)
    files = {}
    for item in data["Items"].get("ModPackageFile", []):
        destination = item["Destination"]
        path = PurePosixPath(destination)
        if not destination or path.is_absolute() or ".." in path.parts or "\\" in destination:
            raise ValueError(f"Invalid archive path: {destination}")
        if destination in files:
            raise ValueError(f"Duplicate archive path: {destination}")
        source = Path(item["FullPath"]).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError(f"Missing or external package input: {source}")
        files[destination] = source
    if not files:
        raise ValueError("No package files declared")
    directory = contained(root, "artifacts/release/v" + version)
    directory.mkdir(parents=True, exist_ok=True)
    name = data["Properties"]["ModPackageName"]
    if Path(name).name != name or not name.endswith(".zip"):
        raise ValueError("ModPackageName must be a ZIP filename")
    archive = directory / name
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as staging:
        temporary = Path(staging.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for destination, source in files.items():
                info = zipfile.ZipInfo(destination, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with source.open("rb") as content, output.open(info, "w") as target:
                    shutil.copyfileobj(content, target)
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
    # Download checksum generated from the archive, never maintained in source configuration.
    with archive.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    (directory / "SHA256SUMS.txt").write_text(f"{digest.hexdigest()}  {name}\n", encoding="utf-8")
    print(archive)
    return archive


def deploy(root: Path, configuration: str) -> None:
    values = evaluate(root, configuration)["Properties"]
    if values["ModPlatform"] != "pc" or not values["GameDir"]:
        raise ValueError("PC deployment requires GameDir in Build.local.props")
    build(root, configuration)
    destination = contained(Path(values["GameDir"]), values["ModDeployDirectory"])
    destination.mkdir(parents=True, exist_ok=True)
    for filename in [values["AssemblyName"] + ".dll", "Utility.dll"]:
        shutil.copy2(Path(values["TargetDir"]) / filename, destination / filename)
    print(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["check", "build", "test", "solution", "deploy", "package", "platform"]
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--configuration", choices=["Debug", "Release"], default="Release")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--expected-version")
    args = parser.parse_args()
    root = args.repo.resolve()
    if args.command == "check":
        project(root)
        run(["dotnet", "tool", "restore"], root)
        run(["dotnet", "tool", "run", "csharpier", "check", "."], root)
    elif args.command == "test":
        for path in tests(root):
            run(["dotnet", "test", str(path), "-c", args.configuration, "--nologo"], root)
    elif args.command == "platform":
        print(evaluate(root)["Properties"]["ModPlatform"] or "library")
    elif args.command == "solution":
        solution(root, args.local)
    elif args.command == "package":
        package(root, args.configuration, args.expected_version)
    elif args.command == "deploy":
        deploy(root, args.configuration)
    else:
        build(root, args.configuration)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
