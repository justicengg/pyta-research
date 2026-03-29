# Branch Conflict Playbook

本文档针对 PYTA Research 的 worktree 开发模式，说明如何在多分支并行开发时安全地合入 main，避免产生冲突。

---

## 当前 Worktree 结构

```
pyta-research/                          ← main 分支（主仓库）
pyta-research-worktrees/
  ├── secondary-market-mvp/             ← feat/secondary-market-mvp 分支
  └── primary-market-mvp/               ← feat/primary-market-mvp 分支（当前）
```

两个 worktree 同时修改了一批**共用文件**，这是合并时冲突的主要来源。

---

## 高风险共用文件

以下文件在两个 worktree 中都有改动，合并时必须逐文件 review：

| 文件 | 冲突风险 | 说明 |
|------|----------|------|
| `frontend/src/components/layout/CanvasStage.tsx` | **高** | primary 加了 `marketMode`/`primaryCanvasState` props；secondary 改过 agent 布局和 interaction panel |
| `frontend/src/pages/ResearchCanvasPage.tsx` | **高** | primary 重写为双模式路由；secondary 有自己的 hook 接入方式 |
| `frontend/src/hooks/useCanvasViewport.ts` | **中** | primary 加了 `initialZoom` 参数；secondary 可能也有改动 |
| `frontend/src/lib/types/canvas.ts` | **中** | primary 新增了 `MarketMode` 类型 |
| `frontend/src/styles/research-canvas.css` | **中** | 两边都加了新样式类 |
| `src/api/app.py` | **低** | primary 加了 primary router；secondary 可能加了别的 router |
| `README.md` | **低** | 两边都有修改 |

新增的纯 primary 文件（`src/sandbox/orchestrator/primary.py`、`frontend/src/components/canvas/primary/` 等）不存在冲突风险。

---

## 合并前必做：冲突预检

**在开 PR 或执行 merge 之前，先跑这一套检查：**

```bash
# 1. 确认当前分支
git branch --show-current

# 2. 拉取最新 main
git fetch origin main

# 3. 检查本分支落后 main 多少个 commit
git rev-list --left-right --count HEAD...origin/main
# 输出: X Y
# X = 本分支领先 main 的 commit 数
# Y = main 领先本分支的 commit 数（Y > 0 说明 main 有新提交，需要处理）

# 4. 查看 main 上有哪些新 commit（如果 Y > 0）
git log HEAD..origin/main --oneline

# 5. 查看哪些文件会有冲突
git diff --name-only HEAD...origin/main
```

---

## 合并策略选择

### 情况 A：main 没有新提交（Y = 0）

直接推，开 PR，fast-forward merge 即可，不会有冲突。

```bash
git push origin <branch-name>
# GitHub 上开 PR → Merge
```

### 情况 B：main 有新提交（Y > 0），但没有碰高风险文件

```bash
git merge origin/main
# 解决冲突（如有）
cd frontend && npm run build
git push
```

### 情况 C：main 有新提交，且触碰了高风险文件

**不要在 GitHub 上用网页编辑器解冲突。** 必须在本地解决：

```bash
git fetch origin main
git merge origin/main

# 冲突文件会被标记，逐文件处理：
git status
```

处理顺序建议：**先解 types → 再解 hooks → 最后解组件**

```
canvas.ts（类型定义）→ useCanvasViewport.ts → CanvasStage.tsx → ResearchCanvasPage.tsx
```

解完每个文件后立即 build 验证：

```bash
cd frontend && npm run build
```

全部解完后：

```bash
git add <resolved-files>
git commit -m "merge: resolve conflicts with origin/main"
git push
```

---

## 解冲突时的判断原则

冲突分两类，处理方式不同：

**1. 纯文本冲突**（两边加了不同的新行，不互相覆盖）
- 直接两边都保留，手动合并

**2. 语义冲突**（两边以不同方式改了同一个逻辑块）
- 以**更新的产品方向**为准，不要机械地选 ours/theirs
- 具体规则：

| 场景 | 保留哪边 |
|------|----------|
| `CanvasStage.tsx` 的 Props 定义 | 合并两边所有新增 prop，不删任何一边 |
| `ResearchCanvasPage.tsx` 的模式路由 | 保留 primary 模式分支，确保 secondary 路由逻辑完整保留 |
| `app.py` 的 router 注册 | 两边的 router 都要保留 |
| CSS 样式 | 两边都保留，不互相覆盖 |

---

## 两个 Worktree 合并到 main 的推荐顺序

同时有 secondary 和 primary 两个分支需要合入 main 时：

**先合 secondary，再合 primary。**

原因：secondary 分支是更早的功能基础，primary 在它之上扩展。先合 secondary 让 main 稳定，再把 primary rebase/merge 到最新 main，冲突范围更可控。

```bash
# Step 1: 合入 secondary（GitHub PR merge）

# Step 2: 在 primary worktree 里同步 main
cd /path/to/primary-market-mvp
git fetch origin main
git merge origin/main   # 在这里解冲突

# Step 3: 解冲突、build、push
cd frontend && npm run build
git add . && git commit -m "merge: sync with main after secondary merge"
git push

# Step 4: 开 primary PR → merge
```

---

## 提交前最终 checklist

- [ ] `git branch --show-current` 确认当前分支
- [ ] `git fetch origin && git rev-list --left-right --count HEAD...origin/main` 检查是否落后
- [ ] 如落后，执行 merge 并解冲突
- [ ] `cd frontend && npm run build` 编译通过（0 errors）
- [ ] 高风险文件逐一确认没有误删对方的代码
- [ ] `git push`
- [ ] GitHub PR 上确认 base branch 是 `main`（不是其他 worktree 分支）

---

## 历史冲突记录

| 时间 | 分支 | 冲突文件 | 原因 | 解法 |
|------|------|----------|------|------|
| 2025-03 | feat/secondary | `CanvasStage.tsx`, `sources.py` | main 前进，分支未同步 | 本地 merge origin/main 后重推 |

> 每次发生冲突后，在上表补充一行，便于后续追溯。
