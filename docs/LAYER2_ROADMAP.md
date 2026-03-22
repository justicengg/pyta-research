# Layer 2 — 沙盘画布开发路线图

> **状态**: 未开始
> **前置条件**: Layer 1 完成（✅ 已完成）
> **参考设计**: Obsidian Vault/PYTA/01 项目主结构/Layer 2

---

## 当前 Layer 2 存在的问题

| 问题 | 描述 |
|------|------|
| Agent 卡片重叠 | 5 个 Agent 节点位置固定，canvas 拉伸后相互遮挡 |
| Toolbar 无用按钮 | 连接来源 / 加载技能 / 加载 Agent / 场景设置 / 运行推演 — 均无实际功能 |
| 结果一次性显示 | 全部 Agent 完成才更新，体验割裂 |
| canvas footer | stage-footer 硬编码开发注释，需要清除 |
| Mock 数据残留 | hint-card 节点内容为 hardcode，需接真实数据 |

---

## 开发任务（按优先级）

### P0 — Canvas 布局修复

**任务 1: 移除 Toolbar 无用按钮**

文件：`frontend/src/components/canvas/CanvasToolbar.tsx`

保留：无（整个 toolbar 可移除，或只保留「运行推演」按钮并接到真实触发逻辑）

**任务 2: Agent 卡片布局重构**

文件：`frontend/src/components/layout/CanvasStage.tsx`

目标布局（参考 5 Agent 围绕中心事件的设计）：

```
              [新闻事件]
                  |
    [传统机构]  [量化机构]  [海外资金]
         \        |        /
          [机构判断] (中心)
         /        |        \
    [散  户]  [短线资金]
```

实现方案：用 CSS Grid 或 absolute positioning 固定 5 个 Agent 位置，不依赖内容撑开。

**任务 3: 移除 stage-footer**

文件：`frontend/src/components/layout/CanvasStage.tsx`

删除底部 `<div className="stage-footer">` 硬编码开发注释。

---

### P1 — Streaming SSE（Agent 结果逐个出现）

**目标**：替代当前 request-response 模式，每个 Agent 完成即推到前端。

**Backend 实现**：

新增端点：`GET /api/v1/sandbox/stream`

```python
from fastapi.responses import StreamingResponse

@router.post("/sandbox/stream")
async def sandbox_stream(body: SandboxRunRequest):
    async def event_generator():
        async for agent_type, result in runner.run_streaming(...):
            yield f"data: {result.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Frontend 实现**：

使用 `EventSource` 或 `fetch` + `ReadableStream` 监听 SSE：

```typescript
const source = new EventSource('/api/v1/sandbox/stream')
source.onmessage = (e) => {
  if (e.data === '[DONE]') { source.close(); return }
  const result = JSON.parse(e.data)
  updateAgentNode(result.agent_type, result)  // 逐个出现
}
```

**UI 效果**：
- Agent 卡片逐个出现（带淡入动画）
- CommandConsole 显示进度（已完成 X / 5）
- 用户可随时点「Stop」关闭 stream，取当前结果

**注意**：
- Streaming 实现后，EventChips 的点击 → 填入 → 运行流程不变
- Timeout 概念从"per-agent timeout"变为"stream timeout"（建议 120s 总时长）
- `useSandboxRun.ts` 需要重写为 streaming 版本

---

### P2 — Agent 节点交互增强

**任务 1: 节点状态动画**
- `initializing` → 骨架屏（shimmer effect）
- `live` → 内容淡入
- `degraded` → 灰色 + 错误提示

**任务 2: 节点展开/收起**
- 默认显示摘要（observations 前 2 条）
- 点击展开查看完整 concerns / analytical_focus
- 类似 Linear issue 详情的交互

**任务 3: Agent 间关系连线**
- 用 SVG 画 Agent → 中心节点的连线
- 连线在 streaming 过程中逐渐出现

---

### P3 — 配置超时（Settings 中加入）

在 `SettingsPopover.tsx` 的 LLM 配置区加一个 Timeout 选项：

```
推演超时
○ 30s   ● 60s   ○ 90s
```

存入 `user_settings` 表（key: `sandbox_timeout_ms`），`useSandboxRun.ts` 读取。

---

## 设计原则（来自 Obsidian Layer 2 笔记）

- **核心场景在中心** — 事件 / 标的在 canvas 中心，Agent 围绕运转
- **最近动作最清晰** — 最新推演结果最突出，历史步骤逐渐淡化
- **最终只把收敛结果送去画布** — 结果卡位在下方，不在节点内展开
- **不带回旧世界** — buy/sell/hold、target price、stop loss、position simulation 一律不出现

---

## 文件清单（Layer 2 主要改动范围）

```
frontend/src/components/layout/CanvasStage.tsx      主要改动
frontend/src/components/canvas/AgentNode.tsx        节点状态动画
frontend/src/components/canvas/CanvasToolbar.tsx    移除无用按钮
frontend/src/hooks/useSandboxRun.ts                 改为 streaming 版本
frontend/src/styles/research-canvas.css             Canvas 布局 CSS
src/api/routers/sandbox.py                          新增 /sandbox/stream 端点
src/sandbox/agents/runner.py                        新增 run_streaming 方法
```
