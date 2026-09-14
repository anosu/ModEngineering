"""One-time migration of the explicitly enumerated maintained workspace repositories."""
from pathlib import Path
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from mod import load, sync, write, within

WORKSPACE = Path(__file__).resolve().parents[2]
PC = ['AbyssMod', 'MuvluvMod', 'OptionalConsumer', 'GCMod']
ANDROID = [name + suffix for name in ['AbyssMod', 'AyarabuMod', 'GCMod', 'MuvluvMod', 'OptionalConsumer', 'TSKHook'] for suffix in ['-Android', '-Android-Variant']]
NAMES = ['Utility', 'OptionalRuntime', *PC, *ANDROID]


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def migrate(name):
    root = within(WORKSPACE, name)
    if (root / 'mod.json').exists():
        print('Already migrated:', name)
        return
    if git(root, 'status', '--porcelain'):
        raise ValueError(f'Dirty repository: {name}')
    tracked = git(root, 'ls-files').splitlines()
    mod = 'Extension' if name == 'OptionalRuntime' else name.split('-Android')[0]
    kind = 'library' if name in NAMES[:2] else 'pc' if name in PC else 'android'
    old_project = 'Extension.csproj' if mod == 'Extension' else f'{mod}/{mod}.csproj'
    project_text = (root / old_project).read_text(encoding='utf-8-sig')
    tests = [p for p in tracked if p.endswith('.csproj') and ('Test' in p) and not p.startswith('shared/')]
    mappings = {}
    for path in tracked:
        if path.startswith(f'{mod}/'):
            mappings[path] = 'src/' + path
        elif mod == 'Extension' and path.startswith('src/'):
            mappings[path] = 'src/Extension/' + path[4:]
        elif path == old_project:
            mappings[path] = f'src/{mod}/{mod}.csproj'
        elif path.startswith(f'{mod}.Tests/'):
            mappings[path] = 'tests/' + path
    config = {'schemaVersion': 1, 'repository': name, 'github': 'anosu/' + name, 'kind': kind, 'assembly': mod, 'project': f'src/{mod}/{mod}.csproj', 'tests': [mappings.get(p,p) for p in tests], 'useExtension': name.endswith('-Variant')}
    if kind == 'android':
        script = (root / 'scripts/build-release.ps1').read_text(encoding='utf-8-sig')
        archive = re.search(r'\$archivePath = Join-Path \$outputDirectory "([^"]+)"', script).group(1)
        font = re.search(r'\$fontBundle = Join-Path \$dependencyRoot "([^"]+)"', script)
        block = re.search(r'\$inputs = \[ordered\]@\{(.*?)\n\}', script, re.S).group(1)
        sources = {'modAssembly': f'output/{mod}.dll', 'utilityAssembly': 'output/Utility.dll', 'adapterAssembly': 'output/Extension.dll'}
        if font:
            sources['fontBundle'] = 'dependencies/' + font.group(1)
        files = [{'destination': dest, 'source': sources[var]} for dest,var in re.findall(r'"([^"]+)"\s*=\s*\$(\w+)', block)]
        if len(files) < 2:
            raise ValueError(f'Cannot parse package layout: {name}')
        config['package'] = {'name': archive, 'files': files}
    elif kind == 'pc':
        config['deployDirectory'] = 'BepInEx/plugins/' + ('' if mod == 'OptionalConsumer' else mod + '/') + '{configuration}/net6.0'
    # Move individual tracked files only. Ignored binaries and local build outputs stay put.
    for old,new in mappings.items():
        source, destination = within(root, old), within(root, new)
        if destination.exists():
            raise ValueError(f'Destination already exists: {destination}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
    project = root / config['project']
    text = project.read_text(encoding='utf-8-sig')
    text = text.replace('Project="../build/', 'Project="$(ModRepositoryRoot)build/')
    text = text.replace('$(MSBuildProjectDirectory)/../dependencies', '$(ModRepositoryRoot)dependencies')
    text = re.sub(r'\s*<BaseOutputPath>.*?</BaseOutputPath>', '', text, flags=re.S)
    if mod == 'Extension':
        text = text.replace('$(MSBuildThisFileDirectory)dependencies', '$(ModRepositoryRoot)dependencies')
        text = text.replace('Compile Include="src/**/*.cs"', 'Compile Include="**/*.cs" Exclude="bin/**;obj/**"')
        text = text.replace('Include="android\\build\\classes.dex"', 'Include="$(ModRepositoryRoot)android/build/classes.dex"')
        text = text.replace('$(MSBuildThisFileDirectory)android\\build\\classes.dex', '$(ModRepositoryRoot)android/build/classes.dex')
    if kind == 'pc':
        assets = root / mod / 'obj/project.assets.json'
        if assets.exists():
            packages = json.loads(assets.read_text(encoding='utf-8'))['libraries']
            for package in ['BepInEx.Unity.IL2CPP','BepInEx.PluginInfoProps']:
                resolved = [p.split('/',1)[1] for p in packages if p.startswith(package+'/')]
                if len(resolved) == 1:
                    text = re.sub(r'(Include="'+re.escape(package)+r'"\s+Version=")[^"]+', lambda m:m[1]+resolved[0], text)
    if kind == 'android':
        info = root / f'src/{mod}/Core/ModInfo.cs'
        content = info.read_text(encoding='utf-8-sig')
        content = content.replace('public static class ModInfo', 'public static partial class ModInfo')
        content,count = re.subn(r'^\s*public const string Version = "[^"]+";\r?\n', '\n', content, flags=re.M)
        if count != 1:
            raise ValueError(f'Cannot migrate version: {info}')
        write(info, content)
        text = text.replace('<PropertyGroup>', '<PropertyGroup>\n        <GenerateModVersion>true</GenerateModVersion>', 1)
    write(project, text)
    for test_path in config['tests']:
        target = root / test_path
        text = target.read_text(encoding='utf-8-sig')
        for separator in ['/', '\\']:
            text = text.replace('..'+separator+mod+separator, '..'+separator+'..'+separator+'src'+separator+mod+separator)
        write(target, text)
    props = root / 'Directory.Build.props'
    text = props.read_text(encoding='utf-8-sig') if props.exists() else '<Project>\n</Project>\n'
    text = text.replace('<Project>', '<Project>\n    <PropertyGroup>\n        <ModRepositoryRoot>$(MSBuildThisFileDirectory)</ModRepositoryRoot>\n    </PropertyGroup>', 1)
    write(props, text)
    write(root / 'mod.json', json.dumps(config,indent=2,ensure_ascii=False))
    for old in tracked:
        if '/' not in old and old.endswith(('.sln','.slnx')):
            (root / old).unlink()
    # Exact known shared project path upgrades, including ignored local overrides.
    for p in [root / 'SharedDependencies.local.props', root / 'SharedDependencies.local.props.example']:
        if p.exists():
            content = p.read_text(encoding='utf-8-sig').replace('Utility/Utility/Utility.csproj','Utility/src/Utility/Utility.csproj').replace('OptionalRuntime/Extension.csproj','OptionalRuntime/src/Extension/Extension.csproj')
            write(p, content)
    ignore = root / '.gitignore'
    old_ignore = ignore.read_text(encoding='utf-8-sig') if ignore.exists() else ''
    write(ignore, old_ignore + '\nartifacts/\n**/bin/\n**/obj/\n*.local.slnx\nSharedDependencies.local.props\nBuild.local.props\n')
    sync(root, config)
    print('Migrated:', name, config['project'], flush=True)


if __name__ == '__main__':
    for name in sys.argv[1:] or NAMES:
        if name not in NAMES:
            raise ValueError('Not in maintenance allowlist: '+name)
        migrate(name)
