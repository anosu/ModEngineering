# 工程规范

各仓库以 `mod.json` 声明项目路径、平台、测试、私有依赖和发布包文件映射。`shared/ModEngineering` 固定工程实现提交，`engineeringRevision` 固定同一提交的 reusable workflow；升级必须同时更新两者。

源码放 `src/<名称>/`，独立测试放 `tests/<名称>.Tests/`。`dependencies/` 只跟踪必要编译引用与发行资源，`artifacts/`、完整 interop、本地方案与本机配置不进入 Git。标准方案使用仓库名 `.slnx`，本地联调方案使用 `.local.slnx`。

C# 统一 CSharpier 1.3.0、4 空格、100 列、LF。新模块启用 nullable；旧游戏 hook 的 nullable 例外保留在项目配置，迁移时真正修复，不用大面积抑制警告。公共 API 写 XML 注释，异步 I/O 传递取消令牌。只有依赖 Unity 的代码可以访问 Unity API，纯缓存与协议代码应独立测试。

运行目标保持 net6.0，工程 SDK 使用支持 slnx 的 .NET 9；测试运行时使用 .NET 8。VS 使用 2022 17.14 或更新版本。SDK 与 NuGet 版本固定，定期通过批量升级验证更新。

Utility 提供共享运行能力，Extension 保持私有。各游戏的 CDN 路径、哈希协议、字典规则、同步加载默认值、通知时机和安装布局保持兼容。公共抽象不能依赖某一个游戏的配置或 Unity 类型。

PC build 默认写入 artifacts，deploy 才复制到游戏目录。Android push/PR 做规范检查、测试和确定性打包验证，不上传 Actions 测试附件；v 标签与唯一项目版本匹配才发布正式 ZIP 和 SHA256SUMS。共享库及 PC 没有自动 Release。

Variant 从标准 Android 合并上游，保留历史和私有行为。公共改进在工程或 Utility 仓库实现一次，再更新消费者固定版本。游戏特有公共代码先进入标准版，合并进对应 Variant。

生成文件通过 `mod.py sync` 更新，CI 的 `mod.py check` 检测漂移。不要逐仓修改生成的配置和工作流。项目已有缓存和用户配置不能随工程迁移清空。
