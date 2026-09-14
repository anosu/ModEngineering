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

Extension 的多个消费者可共用同一个只读 deploy key。将私钥保存到源码仓库之外的本机受保护文件，再运行：

```sh
python shared/ModEngineering/scripts/mod.py extension-secret --key /path/outside/repos/adapter-readonly
```

该命令通过 stdin 将私钥交给 `gh secret set`，不打印或写入仓库。新建消费者只需重复接入命令，无需创建新的 Extension deploy key。共享密钥轮换需要更新所有消费者；未迁移的旧密钥不得提前删除。

详见 [工程规范](docs/CONVENTIONS.md)。
