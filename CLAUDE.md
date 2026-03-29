# PYTA Research — Claude Code 指令

## 开发协同工作流

通过 GitHub PR 和 commit 记录协同开发，不使用 Linear。

## 分支与合并规则

每次推送或合并前，必须阅读并遵守：

**`docs/BRANCH_CONFLICT_PLAYBOOK.md`**

该文档包含：
- 高风险共用文件清单（`CanvasStage.tsx`、`ResearchCanvasPage.tsx` 等）
- 合并前冲突预检命令
- 两个 worktree 合并到 main 的推荐顺序（先 secondary，再 primary）
- 解冲突判断原则
- 提交前最终 checklist

## 数据库

当前 MVP 使用 `Base.metadata.create_all(engine)` 直接建表。生产部署前需接入 Alembic migration。
