# PYTA Research — Agent 指令

## 开发协同工作流

通过 GitHub PR 和 commit 记录协同开发，不使用 Linear。

---

## 分支与合并规则（每次推送前必须执行）

### Worktree 结构

```
pyta-research/                          ← main 分支（主仓库）
pyta-research-worktrees/
  ├── secondary-market-mvp/             ← feat/secondary-market-mvp 分支
  └── primary-market-mvp/               ← feat/primary-market-mvp 分支
```

### 高风险共用文件

以下文件两个 worktree 都有改动，合并时必须逐文件 review，不得机械选 ours/theirs：

| 文件 | 风险 | 说明 |
|------|------|------|
| `frontend/src/components/layout/CanvasStage.tsx` | **高** | primary 加了 `marketMode`/`primaryCanvasState` props；secondary 改过 agent 布局 |
| `frontend/src/pages/ResearchCanvasPage.tsx` | **高** | primary 重写为双模式路由；secondary 有自己的 hook 接入 |
| `frontend/src/hooks/useCanvasViewport.ts` | **中** | primary 加了 `initialZoom` 参数 |
| `frontend/src/lib/types/canvas.ts` | **中** | primary 新增了 `MarketMode` 类型 |
| `frontend/src/styles/research-canvas.css` | **中** | 两边都加了新样式 |
| `src/api/app.py` | **低** | 两边各自注册了不同 router |
| `README.md` | **低** | 两边都有修改 |

### 合并前冲突预检（必跑）

```bash
git branch --show-current
git fetch origin main
git rev-list --left-right --count HEAD...origin/main
# X Y — Y > 0 说明 main 有新提交，必须先处理
git diff --name-only HEAD...origin/main
```

### 合并策略

**Y = 0**（main 没有新提交）：直接推，开 PR。

**Y > 0，未碰高风险文件**：
```bash
git merge origin/main
cd frontend && npm run build
git push
```

**Y > 0，触碰了高风险文件**：
- 禁止在 GitHub 网页编辑器解冲突，必须本地解决
- 解冲突顺序：`canvas.ts` → `useCanvasViewport.ts` → `CanvasStage.tsx` → `ResearchCanvasPage.tsx`
- 每解完一个文件立即跑 `cd frontend && npm run build`
- 全部解完后：`git add` → `git commit` → `git push`

### 解冲突判断原则

| 场景 | 规则 |
|------|------|
| `CanvasStage.tsx` Props 定义 | 合并两边所有新增 prop，不删任何一边 |
| `ResearchCanvasPage.tsx` 模式路由 | primary 模式分支和 secondary 路由逻辑都要保留 |
| `app.py` router 注册 | 两边的 router 都要保留 |
| CSS 样式 | 两边都保留，不互相覆盖 |

### 两个 Worktree 合并到 main 的顺序

**先合 secondary，再合 primary。**

```bash
# Step 1: secondary PR merge 到 main（GitHub 上操作）

# Step 2: primary worktree 同步 main
git fetch origin main
git merge origin/main

# Step 3: 解冲突 → build → push
cd frontend && npm run build
git add . && git commit -m "merge: sync with main after secondary merge"
git push

# Step 4: primary PR merge 到 main
```

### 提交前最终 checklist

- [ ] 确认当前分支名
- [ ] `git fetch origin && git rev-list --left-right --count HEAD...origin/main`
- [ ] 如落后，merge 并解冲突
- [ ] `cd frontend && npm run build` 编译通过（0 errors）
- [ ] 高风险文件逐一确认没有误删对方代码
- [ ] GitHub PR base branch 确认是 `main`

---

## 数据库

当前 MVP 使用 `Base.metadata.create_all(engine)` 直接建表。生产部署前需接入 Alembic migration。
