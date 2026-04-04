# 发布指南

本文档说明了如何为项目发布新版本。

## 版本管理

本项目采用 Semantic Versioning (SemVer) 规范。版本号格式为 `MAJOR.MINOR.PATCH`:

- `MAJOR`: 不兼容的 API 变更
- `MINOR`: 新功能(向后兼容)
- `PATCH`: 错误修复(向后兼容)

示例: `0.1.0`, `1.0.0`, `1.2.3`

## 版本配置

项目版本在 `pyproject.toml` 中定义:

```toml
[project]
name = "etf-trend"
version = "0.1.0"
```

在发布前,更新该文件中的版本号。

## 发布前检查清单

在开始发布流程前,完成以下步骤:

### 1. 代码检查和测试

运行完整的测试套件:

```bash
uv run pytest
```

确保所有测试通过。

### 2. 代码质量检查

运行 linting 和格式化检查:

```bash
uv run ruff check .
uv run black --check . --line-length=100
```

修复任何发现的问题:

```bash
uv run ruff check . --fix
uv run black . --line-length=100
```

### 3. 前端构建

构建前端应用:

```bash
npm run build
```

确保构建成功且没有错误。

## 发布流程

### 第一步: 更新版本号

编辑 `pyproject.toml`,将版本号更新为新版本:

```toml
[project]
name = "etf-trend"
version = "X.Y.Z"
```

### 第二步: 更新变更日志

创建或更新 `CHANGELOG.md` 文件,记录本版本的变更:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- 新功能描述

### Fixed
- 错误修复描述

### Changed
- 行为变更描述

### Deprecated
- 弃用功能描述
```

遵循 [Keep a Changelog](https://keepachangelog.com/) 格式。

### 第三步: 提交变更

提交版本更新和变更日志:

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"
```

### 第四步: 创建版本标签

为发布创建 Git 标签:

```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
```

例如:

```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
```

### 第五步: 推送更改

推送提交和标签到远程仓库:

```bash
git push origin main
git push origin vX.Y.Z
```

### 第六步: 发布

根据你的发布流程,将新版本发布到包管理仓库(如 PyPI)或部署到生产环境。

## 发布检查清单

发布前,确保:

- [ ] 所有测试通过: `uv run pytest`
- [ ] 代码检查通过: `uv run ruff check .`
- [ ] 代码格式化完成: `uv run black . --line-length=100`
- [ ] 前端构建成功: `npm run build`
- [ ] `pyproject.toml` 版本号已更新
- [ ] `CHANGELOG.md` 已更新
- [ ] 版本标签已创建: `git tag -a vX.Y.Z -m "Release version X.Y.Z"`
- [ ] 提交和标签已推送到远程仓库

## 回滚发布

如果发现发布有问题,可以删除标签并重新发布:

```bash
# 删除本地标签
git tag -d vX.Y.Z

# 删除远程标签
git push origin :refs/tags/vX.Y.Z

# 修复问题后重新发布
```

## 常见问题

### 如何处理 patch 版本发布?

对于 patch 版本(如 0.1.0 -> 0.1.1),仅需:

1. 修复 bug
2. 更新版本号为新的 patch 版本
3. 更新变更日志
4. 创建标签并推送

### 如何处理 minor 版本发布?

对于 minor 版本(如 0.1.0 -> 0.2.0),需要:

1. 添加新功能
2. 更新版本号为新的 minor 版本
3. 更新变更日志,列出所有新功能
4. 创建标签并推送

### 如何处理 major 版本发布?

对于 major 版本(如 0.1.0 -> 1.0.0),需要:

1. 进行重大重构或 API 改动
2. 更新版本号为新的 major 版本
3. 更新变更日志,清晰说明破坏性变更
4. 创建标签并推送
5. 可能需要发布迁移指南

## 支持

如有发布相关问题,请提交 Issue 或联系项目维护者。
