# ModEngineering

PC / Android IL2CPP Mod 的公共工程入口，集中维护构建、代码检查、项目生成和 Android 发布流程。运行时通用能力由 Utility 提供。

需要 Python 3.10+、PowerShell 7、.NET SDK 9 和 .NET 8 测试运行时。消费者将本仓库固定为 `shared/ModEngineering` 子模块。

```sh
python shared/ModEngineering/scripts/mod.py sync
python shared/ModEngineering/scripts/mod.py check
python shared/ModEngineering/scripts/mod.py build --configuration Debug
python shared/ModEngineering/scripts/mod.py test
python shared/ModEngineering/scripts/mod.py solution --local
```

Android 使用 `scripts/build-release.ps1` 验证打包；PC 使用 `scripts/deploy.ps1` 构建后部署。普通 push/PR 不上传测试包，Android 版本标签触发正式发布。

升级工程用 `mod.py update --revision <commit>`；升级其他共享子模块增加 `--dependency <目录名>`。命令拒绝脏仓库并验证结果，不自动提交或发布。工作区批量入口为 `scripts/workspace.py`，只处理显式清单中的目录。

## 创建项目

```sh
python scripts/new-mod.py ../ExampleMod-Android --assembly ExampleMod --kind android --github example/ExampleMod-Android
```

`--kind pc` 生成 PC 项目；`--upstream <URL>` 从指定上游派生项目；`--create-remote public|private` 明确指定是否及如何创建远程仓库。游戏代码、依赖和资源映射由消费者维护。

## 可选依赖

额外依赖通过消费者自己的 `mod.json` 中的 `extension` 对象配置：`repository`、`path`、`project`、`localProject`，以及可选的 `secretName`、`packageFiles`。具体地址、名称及访问配置不属于本公共仓库。

生成器可通过 `--extension-config <JSON文件>` 接入该配置。`mod.py extension-secret --key <仓库外的密钥文件>` 设置调用方 secret，密钥仅通过标准输入传给 GitHub CLI。默认密钥文件为 `~/.ssh/extension_deploy_ed25519`，可通过 `MOD_DEPENDENCY_KEY_FILE` 覆盖。

公开仓库不得记录其他项目的非公开信息。模板、测试和文档使用虚构示例；具体部署配置只保留在对应消费者或本机配置中。

详见 [工程规范](docs/CONVENTIONS.md)。
