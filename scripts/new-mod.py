"""Create a standard Mod or derive a Variant repository from an explicit upstream URL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from mod import DEFAULT_DEPENDENCY_KEY, ENGINEERING, local_props, run, solution, sync, write


def scaffold(root: Path, repository: str, assembly: str, kind: str, github: str) -> dict:
    """Write the local, game-independent starter. Git/dependency operations are separate."""
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', assembly):
        raise ValueError('Assembly must be a valid C# identifier')
    if kind not in ('pc', 'android'):
        raise ValueError('Expected pc or android')
    config = dict(schemaVersion=1, repository=repository, github=github, kind=kind, assembly=assembly,
                  project=f'src/{assembly}/{assembly}.csproj', tests=[], useExtension=False)
    write(root / 'Directory.Build.props', '''<Project>
    <PropertyGroup><ModRepositoryRoot>$(MSBuildThisFileDirectory)</ModRepositoryRoot></PropertyGroup>
    <Import Project="$(ModRepositoryRoot)shared/ModEngineering/build/Mod.props" />
</Project>''')
    common = f'''<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <TargetFramework>net6.0</TargetFramework>
        <AssemblyName>{assembly}</AssemblyName>
        <RootNamespace>{assembly}</RootNamespace>
        <Product>{assembly}</Product>
        <Version>1.0.0</Version>
        <Authors>Jitsu</Authors>
        <LangVersion>latest</LangVersion>
        <Nullable>enable</Nullable>
        <ImplicitUsings>enable</ImplicitUsings>
    </PropertyGroup>
    <Import Project="$(ModRepositoryRoot)build/SharedDependencies.props" />
'''
    if kind == 'android':
        common += '''    <PropertyGroup>
        <GenerateModVersion>true</GenerateModVersion>
        <GameInteropReferenceDirectory>$(ModRepositoryRoot)dependencies/interop/assemblies</GameInteropReferenceDirectory>
        <MelonLoaderReferenceDirectory>$(ModRepositoryRoot)dependencies/melonloader/net6</MelonLoaderReferenceDirectory>
    </PropertyGroup>
    <ItemGroup>
        <Reference Include="MelonLoader" HintPath="$(MelonLoaderReferenceDirectory)/MelonLoader.dll" Private="false" />
        <Reference Include="0Harmony" HintPath="$(MelonLoaderReferenceDirectory)/0Harmony.dll" Private="false" />
        <Reference Include="Il2CppInterop.Runtime" HintPath="$(MelonLoaderReferenceDirectory)/Il2CppInterop.Runtime.dll" Private="false" />
        <Reference Include="Assembly-CSharp" HintPath="$(GameInteropReferenceDirectory)/Assembly-CSharp.dll" Private="false" />
        <Reference Include="Il2Cppmscorlib" HintPath="$(GameInteropReferenceDirectory)/Il2Cppmscorlib.dll" Private="false" />
    </ItemGroup>
'''
        source = f'''using MelonLoader;
[assembly: MelonInfo(typeof({assembly}.Core), {assembly}.ModInfo.Name, {assembly}.ModInfo.Version, "Jitsu")]
namespace {assembly};
/// <summary>Game-specific initialization entry point.</summary>
public sealed class Core : MelonMod {{ }}
'''
        write(root/f'src/{assembly}/Core/ModInfo.cs', f'''namespace {assembly};
/// <summary>Mod identity. Version is generated from the project.</summary>
public static partial class ModInfo
{{
    public const string Name = "{assembly}";
    public const string Author = "Jitsu";
}}
''')
        config['package'] = {'name':repository+'.zip','files':[
            {'source':f'output/{assembly}.dll','destination':f'Mods/{assembly}/{assembly}.dll'},
            {'source':'output/Utility.dll','destination':f'Mods/{assembly}/Utility.dll'}]}
    else:
        common += '''    <Import Project="$(ModRepositoryRoot)build/PcBuild.props" />
    <PropertyGroup><RestoreAdditionalProjectSources>https://api.nuget.org/v3/index.json;https://nuget.bepinex.dev/v3/index.json</RestoreAdditionalProjectSources></PropertyGroup>
    <ItemGroup>
        <PackageReference Include="BepInEx.Unity.IL2CPP" Version="$(BepInExVersion)" IncludeAssets="compile" />
        <PackageReference Include="BepInEx.PluginInfoProps" Version="$(BepInExPluginInfoVersion)" />
        <Reference Include="$(GameInteropDir)/*.dll" Private="false" />
    </ItemGroup>
'''
        source = f'''using BepInEx;
using BepInEx.Unity.IL2CPP;
namespace {assembly};
/// <summary>Game-specific initialization entry point.</summary>
[BepInPlugin("jitsu.{assembly.lower()}", MyPluginInfo.PLUGIN_NAME, MyPluginInfo.PLUGIN_VERSION)]
public sealed class Core : BasePlugin
{{
    public override void Load() {{ }}
}}
'''
        config['deployDirectory']=f'BepInEx/plugins/{assembly}/{{configuration}}/net6.0'
        write(root/'Build.local.props.example', '<Project><PropertyGroup><GameDir>PATH_TO_GAME</GameDir></PropertyGroup></Project>')
    write(root/config['project'],common+'</Project>')
    write(root/f'src/{assembly}/Core/Core.cs',source)
    write(root/'.gitignore','artifacts/\n**/bin/\n**/obj/\n.vs/\n*.local.slnx\n*.local.props\ndependencies/interop-backup/\n')
    write(root/'.gitattributes','* text=auto eol=lf\n*.dll binary\n*.dex binary\n')
    write(root/'dependencies/README.md','仅加入当前游戏和加载器必需的编译引用。Android 使用 scripts/sync-dependencies.ps1 同步，完整导出放入忽略的 interop-backup。字体及其他发行资源必须显式加入 mod.json 的 package.files。')
    write(root/'README.md',f'# {repository}\n\n游戏入口位于 `{config["project"]}`。先配置游戏依赖，再运行 `scripts/check.ps1`、`scripts/test.ps1` 和 `scripts/build.ps1`。\n\n共享工程用法见 [ModEngineering](shared/ModEngineering/README.md)。')
    return config


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--assembly')
    parser.add_argument('--kind',choices=['pc','android'],default='android')
    parser.add_argument('--github',required=True,help='owner/repository')
    parser.add_argument('--upstream',help='Explicit standard Android Git URL for a Variant derivative')
    parser.add_argument('--extension-key',type=Path,default=DEFAULT_DEPENDENCY_KEY)
    parser.add_argument('--create-remote',choices=['public','private'])
    args=parser.parse_args()
    root=args.directory.resolve()
    if root.exists(): parser.error('Destination already exists')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',args.github): parser.error('Invalid GitHub repository')
    repository=root.name
    if args.upstream:
        run(['git','clone','--recurse-submodules',args.upstream,str(root)],root.parent)
        run(['git','remote','rename','origin','upstream'],root)
        config=json.loads((root/'mod.json').read_text())
        if config['kind']!='android' or config.get('useExtension'): raise ValueError('Upstream must be a standard Android Mod')
        old_name=config['repository']
        config.update(repository=repository,github=args.github,useExtension=True)
        config['package']['files'].insert(0,{'source':'output/Extension.dll','destination':'Mods/Extension/Extension.dll'})
        text=(root/config['project']).read_text()
        write(root/config['project'],text.replace('<PropertyGroup>','<PropertyGroup>\n        <UseExtension>true</UseExtension>',1))
        old_solution=root/(old_name+'.slnx')
        if old_solution.exists(): old_solution.unlink()
        run(['git','submodule','add','https://github.com/example/optional-runtime.git','shared/Extension'],root)
        run(['git','submodule','update','--init','--recursive','shared/Extension'],root)
    else:
        if not args.assembly: parser.error('--assembly is required for a standard Mod')
        root.mkdir(parents=True)
        config=scaffold(root,repository,args.assembly,args.kind,args.github)
        run(['git','init','-b','main'],root)
        run(['git','submodule','add','https://github.com/anosu/ModEngineering.git','shared/ModEngineering'],root)
        run(['git','submodule','add','https://github.com/anosu/Utility.git','shared/Utility'],root)
        run(['git','submodule','update','--init','--recursive'],root)
    revision=run(['git','rev-parse','HEAD'],ENGINEERING,capture=True)
    run(['git','fetch','origin'],root/'shared/ModEngineering')
    run(['git','checkout','--detach',revision],root/'shared/ModEngineering')
    config['engineeringRevision']=revision
    write(root/'mod.json',json.dumps(config,indent=2))
    sync(root,config)
    sibling_utility = root.parent/'Utility/src/Utility/Utility.csproj'
    sibling_adapter = root.parent/'OptionalRuntime/src/Extension/Extension.csproj'
    if sibling_utility.exists() and (not config.get('useExtension') or sibling_adapter.exists()):
        write(root/'SharedDependencies.local.props',local_props(config))
        solution(root,config,local=True)
    run(['dotnet','tool','restore'],root)
    run(['dotnet','tool','run','csharpier','format','.'],root)
    if args.create_remote:
        if config.get('useExtension') and args.create_remote!='private': parser.error('Variant derivatives must remain private')
        run(['gh','repo','create',args.github,'--'+args.create_remote,'--source',str(root),'--remote','origin'],root)
        if config.get('useExtension'):
            from mod import extension_secret
            extension_secret(root,args.extension_key)
    print(f'Created {root}. Add game dependencies, validate, then commit and push. No release was created.')


if __name__=='__main__': main()
