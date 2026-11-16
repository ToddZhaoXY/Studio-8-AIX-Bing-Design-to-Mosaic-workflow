# 共享版本验证记录

日期：2026-11-16。此记录验证仓库分发和运行前置条件，不把源码/结构检查当作视觉验收。

## 已执行

- 工作台110项Python测试：来源解析、目录、skill导入/快照、CLI路径发现、不同用户目录与CODEX_HOME、配置优先级、受控工具、批量错误/超时/取消、字段差量保存、报告边界。
- ZIP与来源依赖11项Python测试。
- 离线doctor：完整skill v3.6、Library ZIP及manifest/hash、55组件/464选择项/49 Image cards。
- 隔离HTTP smoke：10项通过，涵盖页面、bootstrap、目录、skill、Library页面/manifest/图片摘要、来源及Host限制和无任务创建。
- 前端JavaScript语法检查通过；首次目标选择逻辑检查保证默认workspace为空、不会自动使用作者或列表首项。
- 当前机器的真实只读连接检查：Codex ready、Mosaic已登录且API可达；未创建或修改远端模板。

已从Git创建不含个人配置、缓存和历史输出的全新clone：再次通过110项工作台测试、11项ZIP依赖测试、离线doctor和10项隔离HTTP检查。源ZIP实际从新clone读取，并非复用作者原项目路径。

GitHub Actions配置已保存在 `github-actions-check.yml`，覆盖Python3.9/3.12。发布时已有OAuth凭据缺少workflow权限，SSH连接也不可用，因此该配置尚未放到自动执行目录，未宣称远端CI通过。参见[启用说明](ci.md)。

## 不据此宣称的结果

- 尚未替同事的账号、网络或设备验证Mosaic权限与模型访问。
- 未测试原生Windows；执行器目标是macOS/Linux/WSL。
- 未在此共享发布任务中重新生成464项或把全部卡片做视觉验收。
- 实际生成使用实验性Codex App Server动态工具协议；CLI版本变化仍需实时检查。
- 字体、图标、画布、间距、裁切和交互可能存在差异；未测的响应式、点击和键盘行为保留为未测试。

仓库不包含作者的个人日志、模板ID、workspace、token缓存或运行历史。测试中使用的虚拟标识和skill上游示例不等于给使用者预选的实际目标。
