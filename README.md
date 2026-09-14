# ModEngineering

PC / Android IL2CPP Mod 的公共构建工具。项目设置直接使用 MSBuild，运行时通用能力由 Utility 提供。

需要 Python 3.10+、global.json 指定的 .NET SDK 和 .NET 8 测试运行时。消费者通过 `shared/ModEngineering` Git 子模块引用本仓库；Git 记录依赖版本。

```sh
git submodule update --init --recursive
python shared/ModEngineering/scripts/project.py check
python shared/ModEngineering/scripts/project.py build --configuration Debug
python shared/ModEngineering/scripts/project.py test
python shared/ModEngineering/scripts/project.py package
```

`src/*/*.csproj` 是主项目，`tests/**/*.csproj` 自动作为测试项目。平台、额外发行文件和部署路径由 `.csproj` 的属性与 Item 定义。`global.json`、`.editorconfig` 和工具清单都是原生工具配置。

Android 普通 push/PR 检查、测试、打包但不上传测试包；匹配项目版本的 `v*` 标签自动发布。PC 使用 `project.py deploy` 显式部署，不自动发布。CI 执行当前检出子模块中的本地 composite action，不另存工作流版本。

## 更新依赖

```sh
git submodule update --init --remote shared/ModEngineering shared/Utility
python shared/ModEngineering/scripts/project.py check
python shared/ModEngineering/scripts/project.py test
python shared/ModEngineering/scripts/project.py build
git add shared/ModEngineering shared/Utility
```

检查变更后正常提交。需要选定历史版本时，在相应子模块内使用 `git checkout`。

## 创建与维护项目

可从最接近的现有 Mod 开始，也可使用 `dotnet new classlib` 在 `src/<名称>/` 建立项目并配置加载器引用。普通 Git 子模块管理共享源码；额外依赖、访问设置和资源文件由消费者直接声明。

增加测试项目后，命令行会自动发现它；在 VS 中添加到解决方案，或执行 `project.py solution`。本地共享源码联调可执行 `project.py solution --local`。这些是按需操作，不存在生成文件漂移检查。

公共工具不保存使用者的非公开项目身份和部署信息。

详见 [工程规范](docs/CONVENTIONS.md)。
