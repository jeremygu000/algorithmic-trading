# 贡献指南

感谢你有兴趣为本项目做贡献!本指南将帮助你理解开发工作流程和代码标准。

## 前置要求

在开始之前,请确保你已安装以下工具:

- Python 3.10 或更高版本
- uv (Python 包管理工具)
- Node.js 20 或更高版本
- npm 或 yarn

## 开发环境设置

### 初始化项目

```bash
npm run setup
```

此命令会安装所有依赖并准备开发环境。

### 启动开发服务器

使用以下命令同时启动前后端:

```bash
npm run dev
```

- 后端 API 服务运行在: http://localhost:8300
- 前端应用运行在: http://localhost:3200

如需单独运行:

```bash
npm run api      # 仅启动后端 API
npm run ui       # 仅启动前端
```

## 代码风格

本项目使用以下工具进行代码检查和格式化:

### Python 代码

使用 Ruff 进行 linting 和 Black 进行格式化。

检查代码:

```bash
uv run ruff check .
```

自动格式化代码:

```bash
uv run black . --line-length=100
```

行长度限制为 100 个字符。

### 代码质量检查

运行全面的代码检查:

```bash
npm run check
```

## 测试

运行所有测试:

```bash
uv run pytest
```

在提交 PR 前,确保所有测试都通过。

## 提交消息约定

遵循 Conventional Commits 规范:

- `feat: 新功能描述` - 新功能
- `fix: 错误修复描述` - 错误修复
- `docs: 文档更新描述` - 文档变更
- `style: 代码格式调整描述` - 代码风格变更(不影响逻辑)
- `refactor: 重构描述` - 代码重构(不改变功能)
- `perf: 性能优化描述` - 性能优化
- `test: 测试相关描述` - 测试变更
- `chore: 构建配置描述` - 构建和依赖更新

示例:

```
feat: 添加 ETF 趋势分析功能

添加新的 API 端点用于计算 ETF 价格趋势。

- POST /api/analysis/etf-trend
- 支持多个 ETF 代码输入
- 返回趋势预测结果
```

## Pull Request 流程

1. Fork 项目仓库
2. 创建功能分支: `git checkout -b feature/your-feature-name`
3. 提交你的更改: `git commit -m "feat: your feature"`
4. 推送到分支: `git push origin feature/your-feature-name`
5. 开启 Pull Request

### PR 检查清单

提交 PR 前,请确保:

- 代码通过 `npm run check` 检查
- 所有测试通过: `uv run pytest`
- Python 代码按照风格指南格式化
- 提交消息遵循约定
- PR 描述清晰说明变更内容

## 项目结构

```
.
├── src/
│   ├── web/          # Next.js 前端应用
│   └── api/          # FastAPI 后端服务
├── tests/            # 测试文件
├── pyproject.toml    # Python 项目配置
├── package.json      # Node.js 项目配置
└── README.md         # 项目说明
```

## 获取帮助

如有问题,请:

1. 查阅项目文档
2. 提交 Issue
3. 在 PR 中提问
