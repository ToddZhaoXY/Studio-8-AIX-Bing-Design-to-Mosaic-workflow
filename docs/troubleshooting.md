# 常见问题

## 源库能打开，但不能开始还原

源库预览只需要Python和附带的ZIP。生成还需要Codex与Mosaic都就绪，并明确选择自己的输出workspace。先运行：

```sh
python3 tools/mosaic-workbench/doctor.py
python3 tools/mosaic-workbench/doctor.py --live
```

离线检查通过不代表已登录；实时检查通过也不等于任意卡片的视觉验收。

## 找不到Codex或选中了旧CLI

检查 `command -v codex`、`codex --version`。工作台按显式配置→PATH→已知macOS桌面路径查找。不同CLI可能支持不同App Server协议；使用官方当前版本，或在本地配置中指定已验证的可执行文件。

```json
{"codexBinary": "/absolute/path/to/codex"}
```

保存为 `workbench.local.json` 后重启。不要共享作者的 `.codex` 目录、认证文件或provider密钥。已有 `CODEX_HOME` 用于你自己的配置；工作台不会把它改成仓库目录。

## Codex显示未就绪

在自己的终端中运行 `codex` 完成登录或配置provider，再刷新工作台。OAuth元数据为空不一定代表不能运行：自定义provider会用实际小型推理+工具往返来判断。若provider连接失败、模型不可用或CLI不支持动态工具，查看doctor实时结果；不要把二进制存在或模型列表返回当作生成可用。

## Mosaic连接失败或没有工作区

确认公司网络/VPN与Mosaic权限，运行 `mosaic status`、按提示 `mosaic login`。每人独立登录；仓库不会带作者的workspace ID或token。工作区列表来自当前用户。没有相应权限时需要在Mosaic中获得访问权，不能通过填写别人的ID绕过。

## v1.4等版本无法选择

版本列表来自实时能力。直接创建接口还受当前profile pin约束；未验证的任务级版本切换被禁用。用 `mosaic extensions current` 检查当前配置，并根据你本机的 `mosaic --help` 管理它；工作台不会偷偷切换全局配置。维护既有模板时不要擅自迁移版本。

## 本地预览正常，但Mosaic图片加载失败

Mosaic不能读取这台电脑的`localhost`图片。它使用公开HTTPS资源目录，且目标渲染环境必须能访问。默认资源来自上游公开Library。若团队迁移托管，按原相对路径放置同一套资源，设置 `assetBaseUrl` 并重启；不要把GitHub仓库HTML页面当作图片文件URL。

## 端口占用、从另一个clone打开了旧版本

启动器会核对服务的checkout路径。不同项目不要共用同一端口，可运行：

```sh
./start.sh --port 8771
python3 tools/mosaic-workbench/client.py --url http://127.0.0.1:8771 jobs
```

升级代码前结束当前批次，再停止原服务并重新启动。前台服务用Ctrl+C；后台启动器将自己的PID写入 `tools/mosaic-workbench/state/server-process.json`，先核对PID与路径再停止，不使用全局 `pkill python`。

## 单项失败或超时

程序保留已经创建的模板和本地证据，继续后续项；达到时限不自动宣称成功。查看每项具体错误、最后一次校验及截图。重新发起是新的模板任务，**不会自动接着修改旧草稿**。需要续修时先把该模板ID明确交给助手，按skill读取当前迭代后处理。

## 更新Library或skill

Skill在UI导入完整ZIP并启用，已有任务仍用旧快照。Library可通过本地配置指定兼容ZIP；manifest、构造器hash或注册表结构变化时需要更新适配器，不要删掉校验来强行导入。提交修复时附上脱敏错误、CLI版本和可复现的选择ID，避免提交 `state/`、`outputs/` 或真实认证信息。
