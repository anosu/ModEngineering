# 工程规范

主项目使用 `src/<名称>/<名称>.csproj`；测试通过 `tests/**/*.csproj` 自动发现。项目、平台和发行资源直接配置在 MSBuild 中。Git 子模块是共享依赖版本的唯一记录。

源码放 `src/<名称>/`，独立测试放 `tests/<名称>.Tests/`。`dependencies/` 只跟踪必要编译引用与发行资源，`artifacts/`、完整 interop、本地方案与本机配置不进入 Git。标准方案使用仓库名 `.slnx`，本地联调方案使用 `.local.slnx`。

C# 统一 CSharpier 1.3.0、4 空格、100 列、LF。新模块启用 nullable；旧游戏 hook 的 nullable 例外保留在项目配置，迁移时真正修复，不用大面积抑制警告。公共 API 写 XML 注释，异步 I/O 传递取消令牌。只有依赖 Unity 的代码可以访问 Unity API，纯缓存与协议代码应独立测试。

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

Mod 项目声明 `<ModPlatform>pc</ModPlatform>` 或 `android`；普通共享库无需声明。Version、AssemblyName、RootNamespace 等使用标准 MSBuild 属性。默认 PC 安装目录是 `BepInEx/plugins/<程序集>/<配置>/net6.0`，特殊项目可设置 ModDeployDirectory。

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

打开正常的 `.slnx` 即可使用仓库固定的共享源码。需要联调同级共享工程时，保留 `SharedDependencies.local.props` 中的路径并运行 `project.py solution --local`，打开生成的 `.local.slnx`。本机覆盖不进入 Git；CI 和普通方案使用固定源码。

源项目直接导入 `shared/ModEngineering/build/SharedDependencies.props`，PC 同时导入 PcBuild.props。额外共享项目可通过 ExtensionProjectPath 声明；普通 MSBuild ProjectReference 也可以使用。保留输出隔离，以免多个 Mod 同时构建共享项目时写入同一个中间目录。

## CI 与升级

工作流先检出所需子模块，再执行 `./shared/ModEngineering/.github/actions/build`。平台由项目属性读取；工作流无需复制平台和共享实现的提交号。额外仓库的检出权限由消费者工作流自行处理。

更新共享代码使用 `git submodule update --init --remote shared/ModEngineering shared/Utility`，再执行 `git submodule update --init --recursive`，让嵌套依赖与父项目记录一致。验证后提交 Git 子模块指针。没有额外的同步命令、模板版本或生成文件校验。Android 的测试包不上传，只有版本标签触发发布；PC 保持本地发布。
