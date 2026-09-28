# 工程规范

主项目使用 `src/<名称>/<名称>.csproj`；测试通过 `tests/**/*.csproj` 自动发现。项目、平台和发行资源直接配置在 MSBuild 中。Git 子模块是共享依赖版本的唯一记录。

源码放 `src/<名称>/`，独立测试放 `tests/<名称>.Tests/`。`dependencies/` 只跟踪必要编译引用与发行资源，`artifacts/`、完整 interop、本地方案与本机配置不进入 Git。标准方案使用仓库名 `.slnx`，本地联调方案使用 `.local.slnx`。

Android Mod 固定使用 `dependencies/interop/assemblies/` 保存少量编译 DLL。Android.props 通配引用该目录下的全部 DLL，因此目录内容就是编译依赖清单，增加引用只需复制 DLL。`dependencies/interop-backup/` 保存当前游戏的完整 Interop 导出，不参与构建；该目录只跟踪 `.gitignore`，根目录也忽略整个备份目录，防止重新生成时意外提交导出文件。`dependencies/melonloader/net6/` 保存加载器编译引用。

游戏更新后，先整体替换本机备份，再从仓库根目录执行 `pwsh -NoProfile -File shared/ModEngineering/scripts/sync-dependencies.ps1 -RepositoryRoot . -InteropDirectory dependencies/interop-backup -MelonLoaderDirectory <加载器的net6目录>`。脚本按两个编译目录中已有的 DLL 文件名验证来源并刷新内容，不增删依赖文件。新增引用时从备份复制 DLL 到 `interop/assemblies/`；不再需要的 DLL 直接从该目录删除。只提交最小编译集合，构建和 CI 不读取备份目录。

C# 统一 CSharpier 1.3.0、4 空格、100 列、LF。新模块启用 nullable；旧游戏 hook 的 nullable 例外保留在项目配置，迁移时真正修复，不用大面积抑制警告。注释解释不明显的契约和限制；异步 I/O 传递取消令牌，只有依赖 Unity 的代码可以访问 Unity API。

测试只覆盖有实际回归风险的行为，不为命名、成员存在性、简单转发或机械修改单独增加测试。已有测试失效、重复或只复述实现时应删除，并清理相应依赖。使用与维护说明集中在现有 README、API 和工程规范中，不为每次修改新增实施笔记、验证报告或重复清单。

运行目标保持 net6.0，工程 SDK 使用支持 slnx 的 .NET 9；测试运行时使用 .NET 8。VS 使用 2022 17.14 或更新版本。SDK 与 NuGet 版本固定，定期通过批量升级验证更新。

Utility 提供共享运行能力。各游戏的 CDN 路径、哈希协议、字典规则、同步加载默认值、通知时机和安装布局保持兼容。公共模块不依赖某个游戏的配置；纯数据模块不依赖 Unity。

PC build 默认写入 artifacts，deploy 才复制到游戏目录。Android push/PR 做规范检查、测试和确定性打包验证，不上传 Actions 测试附件；v 标签与唯一项目版本匹配才发布正式 ZIP 和 SHA256SUMS。共享库及 PC 没有自动 Release。

派生项目通过合并上游保留历史。公共改进在工程或 Utility 仓库实现一次，再更新消费者固定版本。具体消费者关系、部署信息和非公开仓库身份不写入公共工程文档、模板或测试。

## 常用命令

```sh
python shared/ModEngineering/scripts/project.py check
python shared/ModEngineering/scripts/project.py test
python shared/ModEngineering/scripts/project.py build --configuration Release
```

Android 打包使用 `project.py package`；PC 显式安装使用 `project.py deploy`。PC 在忽略 Git 的 `Build.local.props` 中设置 GameDir 或 GameInteropDir；纯编译只需要 interop，不会复制文件到游戏。已有游戏缓存和本机配置应保留。

## 项目差异

PC Mod 在 `.csproj` 声明 `<ModPlatform>pc</ModPlatform>`；Android Mod 在 `.csproj` 导入 `shared/ModEngineering/build/Android.props`，获得平台、目标框架、标准依赖路径、基础加载器引用和最小 Interop 目录的通配引用。普通共享库无需声明平台。版本写在 `.csproj`；AssemblyName、Product 和 RootNamespace 默认来自项目文件名，只有不同名时才需要覆盖。默认 PC 安装目录是 `BepInEx/plugins/<程序集>/<配置>/net6.0`，特殊项目可设置 ModDeployDirectory。

新 Android 项目可复制现有项目的根目录工具配置与子模块设置，然后用 `dotnet new classlib` 创建 `src/<名称>/`。将游戏编译所需 DLL 放进 `dependencies/interop/assemblies/`，主项目只需以下基础结构；特殊引用设置、资源和额外发布文件直接加在同一个 `.csproj`：

```xml
<Project Sdk="Microsoft.NET.Sdk">
    <Import Project="$(ModRepositoryRoot)shared/ModEngineering/build/Android.props" />
    <PropertyGroup><Version>1.0.0</Version></PropertyGroup>
    <Import Project="$(ModRepositoryRoot)shared/ModEngineering/build/SharedDependencies.props" />
</Project>
```

`Directory.Build.props` 提供 `ModRepositoryRoot`。这个骨架只在创建时使用；后续构建规则始终从 ModEngineering 导入，不需要同步模板文件。

Android 默认 ZIP 名为 `<程序集>-Android.zip`，包含 `Mods/<程序集>/<程序集>.dll` 和同目录的 Utility.dll。需要其他文件时，在项目中使用普通 MSBuild Target 和 Item：

```xml
<Target Name="CollectExtraPackageFiles" BeforeTargets="GetModPackageFiles">
    <ItemGroup>
        <ModPackageFile Include="$(ModRepositoryRoot)dependencies/font/example-font"
                        Destination="UserData/Example/font" />
    </ItemGroup>
</Target>
```

可通过 ModPackageName 覆盖 ZIP 名称。脚本读取 MSBuild 计算后的路径，不再维护另一份项目、测试或文件清单。版本只在项目中设置；生成的下载校验文件不需要人工维护。

## VS 和共享源码

普通 `.slnx`、直接 `dotnet build` 和工程脚本默认使用仓库固定的共享源码。需要联调同级共享工程时，配置 `SharedDependencies.local.props` 中的路径并运行 `project.py solution --local`，在 VS 或命令行中构建生成的 `.local.slnx`；直接构建项目时显式传入 `-p:UsePinnedSharedDependencies=false`。缺少本地配置、路径无效或依赖与固定源码完全相同时，不生成本地方案。`--local` 仅用于生成方案；工程脚本的构建、测试和打包始终使用固定依赖，CI 也不读取本地覆盖。

`SharedDependencies.local.props` 和 `.local.slnx` 按需保留，不要求每个项目都有，也不进入 Git。`Build.local.props` 仅配置 PC 的游戏、Interop 与部署路径，独立于共享依赖选择，保留现有值。

源项目直接导入 `shared/ModEngineering/build/SharedDependencies.props`，PC 同时导入 PcBuild.props。额外共享项目可通过 ExtensionProjectPath 声明；普通 MSBuild ProjectReference 也可以使用。保留输出隔离，以免多个 Mod 同时构建共享项目时写入同一个中间目录。

## CI 与升级

工作流先检出所需子模块，再执行 `./shared/ModEngineering/.github/actions/build`。平台由项目属性读取；工作流无需复制平台和共享实现的提交号。额外仓库的检出权限由消费者工作流自行处理。

更新共享代码使用 `git submodule update --init --remote shared/ModEngineering shared/Utility`，再执行 `git submodule update --init --recursive`，让嵌套依赖与父项目记录一致。验证后提交 Git 子模块指针。没有额外的同步命令或模板版本。`check` 验证标准 `.slnx` 存在，包含主项目、已发现测试和固定共享项目，且引用有效；不比较生成文件的文本、排序或方案文件夹。测试命令也固定使用仓库依赖，不能由本机路径覆盖。Android 的测试包不上传，只有版本标签触发发布；PC 保持本地发布。
