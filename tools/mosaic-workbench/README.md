# Mosaic 还原工作台

请从仓库根目录的 [README](../../README.md) 开始：那里包含安装、登录、个人配置、启动、批量任务和验证方式。

主入口：`server.py`（HTTP服务）、`launch.py`（启动器）、`client.py`（脚本调用）、`doctor.py`（环境检查）。

执行链路：`codex_engine.py` → `codex_runtime.py` → `mosaic_agent_tools.py`。`engine.py`保留平台I/O与历史恢复辅助函数；其旧autopilot实现不从UI或公开运行入口调用。

生成结果写入当前checkout的`outputs/mosaic-workbench`，缓存与任务索引写入此目录的`state`；二者不提交Git。账号由每位使用者自己的CLI管理。
