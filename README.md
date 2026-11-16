# AIXA · Bing Design Library → Mosaic

带操作界面的本地还原工作台：从 MM Image、AIGC、Video 设计库多选样例，让 **Codex 按版本化 skill，查询 Mosaic 原生组件和规则，使用 Mosaic CLI 创建模板，检查截图并报告差异**。

这是运行在每位使用者电脑上的工具。GitHub 用于分发和协作；无需部署网站，也不需要共享作者的账号。当前实现不是已打包的 Codex plugin，后续可在现有执行接口外增加 plugin 入口。

## 同事拿到仓库后怎么用

### 1. 准备自己的运行环境

- **macOS 或 Linux，Python 3.9+**。Windows 请在 WSL2 内运行完整工作流；原生 Windows 进程管理尚不支持。
- **Codex CLI**：按[官方安装说明](https://developers.openai.com/codex/cli/)安装。可用 `npm install -g @openai/codex`，然后在终端运行 `codex` 完成自己的登录或配置自己的 provider。桌面版附带的 CLI 也可使用。
- **Mosaic CLI**：需可访问 Microsoft Mosaic 的账号、网络和工作区。安装命令来自随附 skill 的[官方配置指引](.agents/skills/mosaic-gen-workflow/references/api-and-iteration-workflow.md)：

  ```sh
  curl -fsSL "https://afd-mosaic-f6e8eycvfaeffkam.b02.azurefd.net/api/cli/install" | bash
  mosaic login
  mosaic status
  ```

  如果当前终端还找不到 `mosaic`，重新打开终端，或使用 `~/.mosaic/bin/mosaic`。Mosaic 可能要求公司网络/VPN。仅有 GitHub 仓库访问权不等于拥有 Mosaic 使用权限。

本工具不安装或修改你的 provider、模型和全局 MCP 设置，不包含账号凭据。生成任务使用你本机配置的 Codex，因此访问权限和用量由你自己的配置决定。

### 2. 下载并检查

```sh
git clone https://github.com/ToddZhaoXY/AIXA-Bing-Design-Library.git
cd AIXA-Bing-Design-Library
python3 tools/mosaic-workbench/doctor.py
```

也可以在 GitHub 上 **Code → Download ZIP**，完整解压后进入目录。仓库已附带约 21 MB 的已验证 Library ZIP 和完整 `mosaic-gen-workflow v3.6`，不需要向作者索要素材；首次启动会建立本地缓存。

`doctor.py` 默认离线检查 Python、源包、skill、55个组件/464个样例的目录和 CLI 路径，不登录、不调用模型、不创建模板。CLI 尚未安装时仍可浏览源库；开始还原前需要两种 CLI 均可用。

如需检查真实连接，可显式运行：

```sh
python3 tools/mosaic-workbench/doctor.py --live
```

真实连接检查会读取自己的账号环境；使用自定义 provider 且没有 OAuth 元数据时，可能运行一次小型只读模型探针。不会创建 Mosaic 模板。Codex 运行层使用 App Server 的实验性动态工具，CLI 需支持该能力；不把“二进制存在”当成“执行链路已验证”。

### 3. 打开工作台

```sh
./start.sh
```

macOS 也可以双击 **启动Mosaic工作台.command**。默认地址为 <http://127.0.0.1:8770>。不想自动打开浏览器时：

```sh
./start.sh --no-browser
```

端口被其他 checkout 占用时，使用 `./start.sh --port 8771`。启动器不会接管其他项目的服务。需要前台运行并用 Ctrl+C 停止时：

```sh
python3 tools/mosaic-workbench/server.py --port 8770
```

### 4. 选择自己的输出位置并运行

1. 搜索或筛选组件，点击原始库预览，再多选。每批最多50项，可一次选择 Image cards 的全部49项。
2. 等待 Codex、Mosaic 连接检查。**首次必须选择你自己的 workspace 和已有文件夹**；也支持手动输入 ID。
3. 选择可用 SDL 版本、名称前缀；可设 Codex 模型、思考强度、每卡时限、最多修复次数，以及补充说明。
4. 点击“让 Codex 开始还原”。默认每卡5分钟、最多1次修复；失败或超时保留草稿并继续下一项。
5. 在任务记录查看模板链接、使用的组件/参考、图标选择和差异。详细验证、截图和执行文件可展开查看。

输入示例：筛选 **Image cards** → 全选 → 前缀 `MM_image_cards` → 选择团队工作区 → 运行。大量任务会持续较久；关闭网页不会停止后台服务，关机、休眠、断网或退出服务会影响执行。需要停止时使用页面的“停止任务”。重启不会擅自重建中断模板，避免重复生成。

## 个人配置（可选）

```sh
cp workbench.example.json workbench.local.json
```

`workbench.local.json` 已加入 `.gitignore`。可指定 CLI 路径、默认工作区/文件夹、兼容源包或图片托管地址；不需要填写全部字段，**不要填密码或 token**。

| JSON 字段 | 环境变量覆盖 | 默认行为 |
| --- | --- | --- |
| `codexBinary` | `MOSAIC_WORKBENCH_CODEX_BIN` | PATH 查找，再检查已知 macOS 桌面 CLI 路径 |
| `mosaicBinary` | `MOSAIC_WORKBENCH_MOSAIC_BIN` | PATH 查找，再检查 `~/.mosaic/bin/mosaic` |
| `workspaceId` | `MOSAIC_WORKSPACE_ID` | 空，由使用者在 UI 选择 |
| `folderId` | `MOSAIC_FOLDER_ID` | `default`，仍以实际可访问文件夹为准 |
| `libraryZip` | `MOSAIC_LIBRARY_ZIP` | 仓库附带的兼容 ZIP |
| `assetBaseUrl` | `MOSAIC_ASSET_BASE_URL` | 已有公开 Library 资源目录 |

CLI 路径可以是绝对路径或相对此仓库的文件路径；不填写时使用自动发现。环境变量优先于本地 JSON。本地配置修改后重启服务。既有 `CODEX_HOME` 会被尊重，不会修改其他应用的配置。

本地 Library 图片能显示，不代表 Mosaic 能访问 `localhost`。目标模板默认引用公开 Library 的 HTTPS 资源；团队更换托管位置时，将同一套资源放到目标渲染器可访问的 HTTPS 目录并设置 `assetBaseUrl`。工具会核对资源与来源摘要，不会把整张卡片截图当还原结果。新 ZIP 若改变内部构造器或目录契约，需要更新提取器；它不是任意 Figma/ZIP 导入器。

## Skill 与版本

- 随仓库提供完整的 [Mosaic Gen Workflow v3.6](.agents/skills/mosaic-gen-workflow/SKILL.md)。Codex 在本项目可读取它，工作台首次启动会建立独立副本。
- UI **Skill → 导入 ZIP → 启用** 可独立更新工作流；运行中任务继续使用启动时冻结的版本。
- [官方更新入口](https://vibehub.microsoft.com/app/anthonyleung-fp-t-a/)可能需要公司访问权限。
- 当前直接写入接口只允许所选 Mosaic profile 的实际 SDL pin；项目新建默认 v1.5。下拉菜单会禁用未验证或后台不支持的版本，**不会为了单次任务切换全局 profile**。
- Skill 的静态样例中若有作者路径或旧接口，以你本机 CLI 路径和实时版本契约为准。

## 实际架构与结果边界

每张卡在独立、临时的 Codex App Server 会话中执行；不是把提示转交给 Mosaic autopilot。Codex通过6个受控工具读取来源和skill、查询原生契约、自己编写JSX/schema/data、保存、看截图并记录差异。来源分段读取，不依赖一次性巨型提示。

程序限制新模板归属、目的地、时间预算和修复次数。一个请求使用一个工作迭代，修复只上传发生变化的字段；报告更新只写本地文件。执行过程不会自动发布模板，也不会编辑别人的既有模板。

“已保存”“结构校验通过”“已取得截图”“Codex画面判断”“用户验收”分别报告。原生画布、图标、字体、间距、裁切和交互可能与 Library 有差异；未验证的响应式、点击和键盘行为不会记为通过。**464项可选择不代表464项已验收**。图库弹窗等能力尚未形成通用完整映射；复杂卡片可能超时或需要后续修改。

本地原型在2026-11-12的两项实测中，3×2单图和5×4三图分别用时4分28秒、4分24秒，均保存为一个迭代并取得实际截图。这是特定环境的历史结果，不是本共享版本在任意账号/网络下的性能或还原保证。共享版本会另外执行离线、干净checkout和连接检查；不会上传作者的历史任务报告。

## 文件与维护

```text
.agents/skills/mosaic-gen-workflow/   完整工作流skill
MM_design_library/                  校验过的来源ZIP与摘要
tools/mosaic-workbench/              本地UI、Codex执行器、受控Mosaic工具
tools/library-to-mosaic/             ZIP校验与来源提取依赖
scripts/                            干净环境验收脚本
outputs/mosaic-workbench/           本机生成结果（忽略）
tools/mosaic-workbench/state/       本机缓存、skill副本、任务索引（忽略）
```

界面和脚本共用执行入口：

```sh
python3 tools/mosaic-workbench/client.py catalog --search single-image
python3 tools/mosaic-workbench/client.py run \
  --select mm-image/image-cards/2x2/single-image \
  --workspace YOUR_WORKSPACE_ID --folder default \
  --prefix MM_image_cards --version v1.5
```

`--select` 可重复，非默认端口使用 `client.py --url http://127.0.0.1:8771 ...`。`--model`省略时使用自己的环境默认模型。

升级前等批次结束或主动停止，再 `git pull` 并重启服务。自己的运行数据、登录和 `workbench.local.json` 不进入 Git；不要用清空整个目录的方式升级。

```sh
python3 -m unittest discover -s tools/mosaic-workbench/tests -v
python3 -m unittest discover -s tools/library-to-mosaic/tests -v
python3 scripts/smoke_test.py
```

[排查常见问题](docs/troubleshooting.md) · [验证记录](docs/verification.md) · [启用可选CI](docs/ci.md) · [内容来源与声明](THIRD_PARTY_NOTICES.md)
