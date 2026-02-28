# pyta-research

PYTA 投研部门投资框架代码仓库。

覆盖市场：A股、港股（主战场）、美股、日股、全球指数基金
投资风格：中长线基本面为主，不做短期博弈，不加杠杆追热点

## 文档索引

| 文档 | 说明 |
|------|------|
| [FRAMEWORK.md](docs/FRAMEWORK.md) | 框架总览 |
| [USAGE.md](docs/USAGE.md) | 如何调用、参数、示例 |
| [CHANGELOG.md](docs/CHANGELOG.md) | 版本变化 |
| [FAQ.md](docs/FAQ.md) | 常见问题 |

## 工具链

- **Linear**: 任务中枢 — [PYTA workspace](https://linear.app/ainews)
- **GitHub**: 代码与版本控制
- **飞书**: 知识沉淀与看板

## 分支策略

- `main`: 受保护主分支，需 PR review 才能合并，禁止 force push
- 功能分支命名: `<owner>/<inv-N>-<short-description>`

## 开发流程

1. Linear Issue 进入 Planned 后，从 Issue 复制 branch name
2. 基于 `main` 创建功能分支
3. 开发完成后提交 PR，使用 PR template 填写信息
4. Review 通过后 merge，Linear Issue 自动关联
