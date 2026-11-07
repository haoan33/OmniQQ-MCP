# HaoAn Lab 发布接入

网站：https://ahmustudyhelper.xyz；产品标识：`omniqq-mcp`。

本项目使用网站版本管理，`runtime_mode=none`、`auth_mode=none`、`download_mode=direct`。网站维护版本日志、安装说明、当前展示版本与撤回记录；本程序不调用网站运行接口、不联网检查权限或强制更新。

## 日常发布

提交业务改动并保持 main 干净，补齐 CHANGELOG.md 的新版本章节后运行：

```powershell
./release.ps1 1.2.3 -DryRun
./release.ps1 1.2.3
```

版本文件为 pyproject.toml 的 project.version 与 napcat_mcp/__init__.py 的 __version__，脚本只更新这两个声明。标签触发 `.github/workflows/release.yml`，测试并构建 universal/universal wheel，上传不可变公开安装包、SHA-256 与 manifest，然后通过短时 GitHub OIDC 同步网站。只需 GitHub Actions 自带权限，无网站管理员或数据库密钥。

网站后台可以编辑网站日志、安装说明、选择展示版、撤回当前版并恢复旧版；这些操作不修改 GitHub 附件，不影响已安装的程序。再次同步同一版本不会覆盖后台已编辑的文字或复活撤回版本。

当前接入配置不创建新版本、不改动既有标签或发行包。历史版本由网站导入；v1.0.1 没有独立安装包，仅保留日志。后续首次新标签的实际自动发布须按工作流结果验收。
