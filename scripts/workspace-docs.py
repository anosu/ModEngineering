"""Refresh only the generated project table in a workspace README."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--inventory", type=Path, required=True)
args = parser.parse_args()
root = args.inventory.resolve().parent
rows = ["| 仓库 | 类型 | 项目版本 | 共享运行库 |", "| --- | --- | --- | --- |"]
for name in json.loads(args.inventory.read_text(encoding="utf-8")):
    repo = (root / name).resolve()
    if not repo.is_relative_to(root):
        raise ValueError("Inventory path escaped workspace")
    config = json.loads((repo / "mod.json").read_text(encoding="utf-8"))
    project = (repo / config["project"]).resolve()
    if not project.is_relative_to(repo):
        raise ValueError("Project path escaped repository")
    version = ET.parse(project).getroot().findtext("PropertyGroup/Version") or "SDK 默认 1.0.0"
    libraries = (
        "—"
        if config["kind"] == "library"
        else "Utility、Extension"
        if config.get("extension")
        else "Utility"
    )
    rows.append(f"| [{name}]({name}/) | {config['kind']} | {version} | {libraries} |")
readme = root / "README.md"
text = readme.read_text(encoding="utf-8")
start = "<!-- mod-projects:start -->"
end = "<!-- mod-projects:end -->"
if text.count(start) != 1 or text.count(end) != 1:
    raise ValueError("README must contain one project-table marker pair")
prefix, remainder = text.split(start, 1)
_, suffix = remainder.split(end, 1)
readme.write_text(
    prefix + start + "\n\n" + "\n".join(rows) + "\n\n" + end + suffix,
    encoding="utf-8",
    newline="\n",
)
