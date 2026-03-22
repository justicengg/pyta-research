# Layer 2 沙盘画布 — 开发交接文档

> **Last updated**: 2026-03-22
> **Branch**: `PYTA/secondary-market-mvp`
> **Status**: Layer 2 核心完成 · Direction A（多轮推演）已上线 · SSE Streaming 待实现

---

## 1. Layer 2 已完成内容总览

### ✅ 画布基础架构

| 功能 | 文件 | 说明 |
|------|------|------|
| 无限画布（平移 + 缩放） | `frontend/src/hooks/useCanvasViewport.ts` | CSS transform translate+scale；pointer 拖拽平移；imperative wheel 监听（passive: false）；zoom-to-cursor 算法；pinch 支持（ctrlKey）；min 0.3× max 2.5× |
| Agent 节点轨道布局 | `frontend/src/lib/mock/canvasState.ts` | 椭圆轨道（Rx=280, Ry=200, center=550,300），五边形布局，5 个 Agent 均匀分布在 12/2/4/8/10 点位置 |
| Agent 节点可拖拽 | `frontend/src/components/canvas/AgentNode.tsx` | pointer events + setPointerCapture；zoom 修正（rawDx / zoom）；stopPropagation 防止触发画布平移 |
| 边连线（flowchart） | `frontend/src/components/canvas/EdgeLayer.tsx` | SVG cubic Bézier；5 条 spoke（Agent → center）+ 3 条 peer（Agent 间影响）；hover 显示 label；拖拽 Agent 时连线实时更新 |
| 拖拽工具栏 | `frontend/src/components/canvas/CanvasToolbar.tsx` | 可拖拽（offset state）；可隐藏（hidden state）；场景设置 + 重置视图 + 缩放% + 运行推演 |
| Zone 三区布局 | `frontend/src/components/layout/CanvasStage.tsx` | Zone A（标题栏）+ Zone B（画布）+ Zone C（CommandConsole）；Toolbar 和 EventChips 在 canvas-layer 外，不随 pan/zoom 移动 |

### ✅ Direction A — 多轮推演循环

| 功能 | 文件 | 说明 |
|------|------|------|
| 轮次追踪 | `frontend/src/hooks/useSandboxRun.ts` | `currentRound` + `roundHistory: RoundRecord[]`；每轮结果追加到历史 |
| LLM 上下文传递 | `useSandboxRun.ts` | 将历史轮次 agent summaries 构建成 context 字符串，拼入 `narrative_guide` 传给后端；LLM 可以看到前轮立场进行修正 |
| 轮次时间轴 | `frontend/src/components/layout/CommandConsole.tsx` | 已完成轮用实心绿点显示，当前轮用虚线圈；收敛质量徽章（已收敛 / 部分收敛 / 待优化）；上一轮核心观点提示 |
| Agent 轮次徽章 | `frontend/src/components/canvas/AgentNode.tsx` | 每个 Agent 卡片左上角显示 R1/R2 徽章，标明数据来自第几轮 |
| 运行按钮状态 | `CommandConsole.tsx` | 第一轮显示「运行推演」，后续显示「第 N 轮推演」 |

### ✅ 类型系统

```typescript
// canvas.ts 新增
type RoundRecord = {
  round: number
  narrative: string
  agentSummaries: Record<string, string>
  quality: 'complete' | 'partial' | 'degraded'
  timestamp: string
}

// AgentCardData 新增字段
round?: number  // 来自第几轮推演
```

---

## 2. 当前架构示意

```
ResearchCanvasPage
├── useSandboxRun()           # 状态管理：轮次 + canvas state + 推演触发
│   ├── currentRound: number
│   ├── roundHistory: RoundRecord[]
│   └── submit() → buildPreviousContext() → POST /api/v1/sandbox/run
│
├── InformationPanel (Layer 1)
│   ├── Sources / EventChips
│   └── SettingsPopover (Portal)
│
└── CanvasStage (Layer 2)
    ├── useCanvasViewport()   # pan + zoom
    ├── agentPositions state  # 可拖拽位置（lifted from AgentNode）
    │
    ├── Zone A: stage-head (标题 + 状态chip)
    ├── Zone B: .stage (无限画布)
    │   ├── .canvas-layer (transform: translate + scale)
    │   │   ├── CanvasBackground (SVG 网格)
    │   │   ├── EdgeLayer (SVG 连线，跟随 agentPositions 更新)
    │   │   ├── center-core (中心标的卡片)
    │   │   └── AgentNode × 5 (可拖拽 + R1/R2 徽章)
    │   ├── CanvasToolbar (fixed，在 canvas-layer 外)
    │   └── EventChips (fixed，在 canvas-layer 外)
    │
    └── Zone C: CommandConsole
        ├── round-timeline (轮次点)
        ├── prev-round-hint (上轮核心观点)
        └── textarea + run-btn
```

---

## 3. 关键技术决策记录

### 3.1 Toolbar 必须在 canvas-layer 外

**问题**：Toolbar 放在 `.canvas-layer` 内会随 pan/zoom 移动。
**方案**：Toolbar 作为 `.stage` 的直接子元素（`canvas-layer` 的兄弟节点），position: absolute 相对 stage 定位。
**注意**：Toolbar 内所有 button 需要 `data-no-pan` 属性，防止 `useCanvasViewport` 的 pointerDown handler 误判为画布平移。

### 3.2 Wheel 事件必须用 imperative listener

React 合成事件默认注册为 passive，无法在其中调用 `e.preventDefault()`，会导致页面跟随 wheel 事件滚动。必须：

```typescript
useEffect(() => {
  el.addEventListener('wheel', onWheel, { passive: false })
  return () => el.removeEventListener('wheel', onWheel)
}, [stageRef])
```

### 3.3 Zoom-to-cursor 算法

```typescript
const scale = newZoom / prev.zoom
const newPanX = cx - (cx - prev.panX) * scale
const newPanY = cy - (cy - prev.panY) * scale
```

其中 `cx, cy` 是鼠标相对于 stage 元素的坐标（减去 `getBoundingClientRect().left/top`）。

### 3.4 Agent 拖拽时连线实时跟随

Agent 位置状态（`agentPositions`）在 `CanvasStage` 层 lift，同时传给 `AgentNode`（用于渲染位置）和 `EdgeLayer`（用于计算连线端点）。拖拽时调用 `handleAgentDragMove(id, dx/zoom, dy/zoom)` 更新状态，EdgeLayer 自动重新计算。

### 3.5 多轮 LLM 上下文格式

```
[历史推演上下文]
第 1 轮（让这 5 个市场参与者继续推演…）
  - traditional_institution: 机构视角偏谨慎…
  - offshore_capital: 海外资金更在意全球流动性…
  ...

[本轮指令]
基于当前情况，假设港股情绪进一步恶化，各 Agent 如何调整立场？
```

---

## 4. 已知问题 & 限制

| 问题 | 严重程度 | 建议处理 |
|------|----------|---------|
| 轨道布局基于 mock 固定坐标 | 中 | 接真实 API 后，从 DB 读取或首次加载时按算法分配位置 |
| 拖拽后刷新页面，位置重置 | 低 | 用 localStorage 缓存 `agentPositions`，key 按 session_id |
| EventChips 数据仍为 mock | 中 | 接 `/api/v1/sources/events` 替换，Layer 1 API 已就绪 |
| CommandConsole 绝对定位在 stage 内 | 低 | 移到 zone-C 独立区域后，stage 高度自动适配 |
| agent_round_badge 仅在 mock 初始数据中 undefined | 低 | 初始状态不显示徽章，首次推演后才出现，符合预期 |
| SSE Streaming 未实现 | 高 | 见 Section 5 |

---

## 5. 下一步开发优先级

### P0 — SSE Streaming（最高价值，改变用户体验）

**后端**：新增 `POST /api/v1/sandbox/stream`，每个 Agent 完成即 yield SSE 事件，不等全部完成。

```python
# src/sandbox/agents/runner.py — 新增方法
async def run_streaming(self, request):
    tasks = {asyncio.create_task(agent.run(request)): agent_id for agent_id, agent in self.agents.items()}
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield result  # 前端实时收到每个 Agent 结果
```

**前端**：`useSandboxRun` 改为 `EventSource` 版本，Agent 卡片逐个「弹出」（淡入动画）。

```typescript
// 替换 fetch POST 为 EventSource
const source = new EventSource('/api/v1/sandbox/stream?...')
source.onmessage = (e) => {
  const agentResult = JSON.parse(e.data)
  setCanvasState(prev => updateAgent(prev, agentResult, currentRound))
}
```

**UI 效果**：
- 推演中，各 Agent 卡片按完成顺序逐一出现（带 200ms 淡入）
- CommandConsole 显示「已完成 3/5」进度
- 「停止」按钮关闭 stream，取当前已返回的结果
- Agent 卡片增加「思考中...」骨架屏状态（shimmer）

### P1 — 收敛摘要卡片

多轮推演结束后，在 center-core 下方生成「收敛结果」小卡：各 Agent 观点的最大公约数摘要，由后端综合生成。

### P2 — 场景参数 Modal（场景设置按钮）

`CanvasToolbar` 中「场景设置」按钮目前无绑定。需要 Modal：

```
标的（Ticker）: [0700.HK        ]
市场：         [港股            ]
时间跨度：     [3个月    6个月  ]
叙事方向：     [ textarea       ]
```

保存后存入 session state，传入 `runSandbox` 请求。

### P3 — Agent 节点状态动画

```css
/* shimmer 骨架屏 */
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position:  200% 0; }
}
.agent-loading {
  background: linear-gradient(90deg, var(--surface-subtle) 25%, var(--border-subtle) 50%, var(--surface-subtle) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
```

---

## 6. 项目文件速查

```
# Backend
src/api/app.py                           FastAPI 入口（仅注册 3 个 router）
src/api/routers/sandbox.py               POST /sandbox/run（60s timeout）
src/sandbox/agents/runner.py             asyncio.gather 并发 5 Agent
src/sandbox/agents/templates/            每个 Agent 的 prompt 模板
src/sandbox/llm/client.py               LLM 调用（DB 配置 > .env > 默认值，think 标签剥离）
src/sources/catalog.json                 Provider 配置（新增 provider 只改此文件）

# Frontend — Layer 1
frontend/src/components/layout/InformationPanel.tsx
frontend/src/components/layout/AddSourceModal.tsx
frontend/src/components/layout/SettingsPopover.tsx
frontend/src/components/canvas/EventChips.tsx

# Frontend — Layer 2
frontend/src/components/layout/CanvasStage.tsx          主画布入口（三区布局）
frontend/src/components/canvas/AgentNode.tsx            Agent 节点（可拖拽 + R徽章）
frontend/src/components/canvas/EdgeLayer.tsx            SVG 连线（Bezier + hover label）
frontend/src/components/canvas/CanvasToolbar.tsx        可拖拽工具栏
frontend/src/components/canvas/CanvasBackground.tsx     点阵 / 网格背景
frontend/src/components/layout/CommandConsole.tsx       多轮控制台（含轮次时间轴）
frontend/src/hooks/useCanvasViewport.ts                 pan + zoom hook
frontend/src/hooks/useSandboxRun.ts                     推演状态 + 多轮历史
frontend/src/lib/types/canvas.ts                        所有 canvas 类型（含 RoundRecord）
frontend/src/lib/mock/canvasState.ts                    Mock 状态 + 轨道布局坐标
frontend/src/styles/research-canvas.css                 全部 UI 样式
```

---

## 7. 设计原则（勿破坏）

1. **不带回旧世界** — buy/sell/hold、target price、portfolio simulation 一律不出现
2. **核心场景在中心** — center-core 是锚点，5 个 Agent 围绕运转
3. **Toolbar 在 canvas-layer 外** — 否则会随 pan/zoom 移动
4. **wheel listener 必须 passive: false** — 不然无法阻止页面滚动
5. **MiniMax base_url 必须含 `/v1`** — `https://api.minimaxi.com/v1`（无末尾斜杠）
6. **api_key 不回传前端** — 只返回 `{configured: bool}`

---

## 8. 快速启动

```bash
# 克隆并切换到 Layer 2 主分支
git clone https://github.com/justicengg/pyta-research
git checkout PYTA/secondary-market-mvp

# Backend
poetry install
poetry run uvicorn src.api.app:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# 设置 LLM（一次性）
curl -X POST http://localhost:8000/api/v1/settings/llm \
  -H 'Content-Type: application/json' \
  -d '{"base_url":"https://api.minimaxi.com/v1","model":"MiniMax-M2.7","api_key":"YOUR_KEY"}'
```

---

*文档由 Claude Sonnet 4.6 生成于 2026-03-22，基于本次开发 session 的完整代码状态。*
