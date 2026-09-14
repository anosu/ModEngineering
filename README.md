# ModEngineering

PC / Android IL2CPP Mod 的公共工程入口。运行时能力位于 Utility，私有 Android 适配位于 OptionalRuntime。

需要 Python 3.10+、PowerShell 7、.NET SDK 9 和 .NET 8 测试运行时。消费者将本仓库固定为 `shared/ModEngineering` 子模块。

在消费者根目录运行：

```sh
python shared/ModEngineering/scripts/mod.py sync
python shared/ModEngineering/scripts/mod.py check
python shared/ModEngineering/scripts/mod.py build --configuration Debug
python shared/ModEngineering/scripts/mod.py test
python shared/ModEngineering/scripts/mod.py solution --local
```

`scripts/*.ps1` 提供同等入口。Android 运行 `scripts/build-release.ps1` 本地验证打包；PC 使用 `scripts/deploy.ps1` 构建后部署。CI 永远使用固定共享源码，不读取本地覆盖。

更新工程：`mod.py update --revision <commit>`。命令拒绝脏工作区，更新子模块、工作流版本和生成文件，然后检查、测试、构建；失败时保留可检查的改动，不自动提交、回滚或发布。

更新运行库使用 `mod.py update --dependency Utility --revision <commit>`，Extension 同理。工作区可以用一个 JSON 数组列出参与维护的仓库相对目录，再执行 `scripts/workspace.py upgrade --inventory <清单.json> --dependency ModEngineering --revision <commit>`；不在清单中的目录不受影响。

新建标准项目：

```sh
python scripts/new-mod.py ../ExampleMod-Android --assembly ExampleMod --kind android --github anosu/ExampleMod-Android
```

将 `--kind` 改为 `pc` 可生成 PC 项目。生成器创建本地 Git 仓库、固定共享子模块和工程入口；游戏 hook、游戏依赖及资源映射仍需按实际游戏补充。增加 `--create-remote public` 可同时建立公开远程仓库。

生成对应 Variant 项目时，用 `--upstream https://github.com/anosu/ExampleMod-Android.git --github anosu/ExampleMod-Android-Variant --create-remote private`。它克隆标准版历史、配置 upstream、加入 Extension，并自动配置依赖 secret。Extension 的游戏专属处理器需要自行实现，生成器不猜测 DMM SDK 或游戏接口。

Extension 的多个消费者可共用同一个只读 deploy key。将私钥保存到源码仓库之外的本机受保护文件，再运行：

```sh
python shared/ModEngineering/scripts/mod.py extension-secret --key /path/outside/repos/adapter-readonly
```

该命令通过 stdin 将私钥交给 `gh secret set`，不打印或写入仓库。新建消费者只需重复接入命令，无需创建新的 Extension deploy key。共享密钥轮换需要更新所有消费者；未迁移的旧密钥不得提前删除。

默认密钥文件为 `~/.ssh/extension_deploy_ed25519`，可用 `MOD_DEPENDENCY_KEY_FILE` 环境变量或 `--key` 覆盖。批量设置使用 `scripts/workspace.py extension-secret --inventory <清单.json>`。该操作不生成新密钥，也不修改 Extension 上已有密钥。

详见 [工程规范](docs/CONVENTIONS.md)。
