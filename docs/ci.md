# 可选：启用GitHub Actions

本仓库已附上[完整检查配置](github-actions-check.yml)，它只运行离线测试、来源检查和本机HTTP smoke，不需要任何Codex或Mosaic账号，不生成模板。

发布时本机的GitHub OAuth登录缺少 `workflow` scope，因此先以普通文件保存配置；当前没有自动运行的Actions工作流，也不宣称远端CI已通过。本地干净clone已通过的检查见[验证记录](verification.md)。

仓库维护者可以在GitHub网页中新建 `.github/workflows/check.yml`，粘贴配置文件的完整内容并提交；也可以使用具备相应权限的Git登录，将文件复制到该路径后推送：

```sh
mkdir -p .github/workflows
cp docs/github-actions-check.yml .github/workflows/check.yml
git add .github/workflows/check.yml
git commit -m "ci: enable offline workflow checks"
git push
```

启用后检查Python3.9与3.12两种环境。不要为此把个人账号凭证或真实运行日志上传到仓库。
