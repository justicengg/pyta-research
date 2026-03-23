# Layer 2 沙盘画布 — 开发交接文档

> **Last updated**: 2026-03-22（今日大改版）
> **Branch**: `PYTA/secondary-market-mvp` → 已 merge → `main`
> **PR**: [#69](https://github.com/justicengg/pyta-research/pull/69)
> **Status**: 拓扑画布 + UX 精简完成 · LLM timeout 已修复 · 信息层基础建设待启动

---

## 1. 今日完成内容（2026-03-22）

### ✅ 动态拓扑布局（最大改动）

| 功能 | 文件 | 说明 |
|------|------|------|
| 同心环拓扑算法 | `frontend/src/hooks/useTopologyLayout.ts` | Ring-1=310px / Ring-2=540px / Ring-3=750px；TOPOLOGY_CENTER=(600,450)；5 次 pushApart 迭代防重叠；CENTER_OBSTACLE 固定障碍防止 agent 卡覆盖中心卡 |
| 第二轮子节点生成 | `frontend/src/hooks/useSandboxRun.ts` | `mergeCanvasState` diff 前后 summary；summary 变化时生成 ring:2 子节点 + `derivation` 虚线边 |
| 边类型扩展 | `frontend/src/components/canvas/EdgeLayer.tsx` | `spoke / peer / derivation / synthesis`；derivation = 细虚线，父节点色调，0.35 透明度 |
| 拓扑 + 拖拽叠加 | `frontend/src/components/layout/CanvasStage.tsx` | `computedPositions`（来自 useTopologyLayout）+ `dragOverrides`（用户手动拖拽）最终合并 |

**关键参数**（不要随意改动）：
```typescript
TOPOLOGY_CENTER = { x: 600, y: 450 }   // 必须与 CSS .center-core { top: 50% } 对齐
RING_RADIUS = { 1: 310, 2: 540, 3: 750 }
CARD_H = 200   // 实际折叠高度，影响 Ring-2 最小半径计算（≥ R1 + CARD_H + 30 = 540）
CENTER_OBSTACLE = { left:480, top:370, right:720, bottom:530 }  // 中心卡占位区
```

**碰撞矩阵结论**（collision tester 验证）：
- Ring-1 × Ring-1：10 对，全部 CLEAR ✓
- Ring-1 × CENTER：5 对，全部 CLEAR ✓
- Ring-2 × Ring-2：10 对，全部 CLEAR ✓
- Ring-2 × 各自父节点：5 对，全部 CLEAR（ΔR=230px > CARD_H=200px）✓
- Ring-2 节点部分超出 canvas 边界（顶部 190px，右侧 214px）→ 设计预期，canvas 可平移

---

### ✅ UX 精简

| 改动 | 说明 |
|------|------|
| CanvasToolbar 完全移除 | 不再渲染；运行按钮整合进 CommandConsole |
| 角落迷你控件 | `canvas-corner-controls`：zoom% 读数 + ⌖ 重置按钮，固定在 `.stage` 右下角 |
| EventsPanel（新组件） | `frontend/src/components/layout/EventsPanel.tsx`；Layer 3 右侧滑动抽屉，`position: fixed`，不随画布移动；通过控制台"事件" chip 切换开/关 |
| CommandConsole 重构 | "事件" chip → 按钮，触发 `onEventsToggle`；运行按钮 `▶ 推演`（去掉冗余轮次数字）；EventChips 从 canvas 移出 |

---

### ✅ 后端修复

| 修复 | 文件 | 说明 |
|------|------|------|
| LLM timeout 20s → 60s | `src/sandbox/llm/client.py` | MiniMax-M2.7 实测耗时 28-35s，原 20s 导致全部 degraded |
| 数据源扩展 | `src/sources/adapter.py` / `catalog.json` / `store.py` | 增加更多 provider 支持 |
| user_settings API | `src/api/routers/user_settings.py` | 新增字段 |

**验证结果（NVDA 推演测试）**：
```
HTTP 200  (28.0s)
data_quality : complete
stop_reason  : all_perspectives_received
5 agents: traditional_institution / quant_institution / retail / offshore_capital / short_term_capital
全部 live ✓
```

---

## 2. 当前架构（最新状态）

```
ResearchCanvasPage
├── useSandboxRun()
│   ├── currentRound / roundHistory: RoundRecord[]
│   ├── prevSummaries diff → 生成 ring-2 子节点 + derivation 边
│   └── submit() → POST /api/v1/sandbox/run（60s timeout）
│
├── InformationPanel (Layer 1)
│   ├── Sources 列表 / AddSourceModal
│   └── SettingsPopover (Portal)
│
└── CanvasStage (Layer 2)
    ├── useCanvasViewport()         # pan + zoom
    ├── useTopologyLayout(agents)   # 同心环坐标计算（pure useMemo）
    ├── dragOverrides state         # 用户手动拖拽覆盖
    ├── eventsPanelOpen state       # Layer 3 面板开关
    │
    ├── Zone A: stage-head（标题 + 状态 chip）
    ├── Zone B: .stage（无限画布）
    │   ├── .canvas-layer（transform: translate + scale）
    │   │   ├── CanvasBackground（SVG 网格）
    │   │   ├── EdgeLayer（spoke / peer / derivation 边）
    │   │   ├── CenterCoreCard（可编辑 ticker/market/narrative）
    │   │   └── AgentNode × N（ring-1 + ring-2，可拖拽）
    │   └── canvas-corner-controls（zoom% + ⌖ reset，不随画布移动）
    │
    ├── Zone C: CommandConsole
    │   ├── cmd-timeline（轮次点 + 收敛质量徽章）
    │   ├── cmd-context（事件 chip[→EventsPanel] + 历史轮次 chip + 5 Agents chip）
    │   └── cmd-input（textarea + ▶ 推演按钮）
    │
    └── EventsPanel（Layer 3，position:fixed 右侧抽屉）
        ├── 事件列表（fetch /api/v1/sources/events）
        └── 点击事件 → 填入指令框 + 关闭面板
```

---

## 3. 关键技术决策记录

### 3.1 TOPOLOGY_CENTER 必须与 CSS center-core 对齐

**已知 Bug（已修复）**：center-core 曾是 `top: 270px`，但 TOPOLOGY_CENTER.y=450，导致 spoke 边连接到错误位置。

**正确做法**：
```css
.center-core { top: 50%; }   /* 50% of canvas-layer height 900px = 450px ✓ */
```
```typescript
export const TOPOLOGY_CENTER = { x: 600, y: 450 }  // 600 = 1200/2, 450 = 900/2
```

### 3.2 Ring-2 最小半径推导

```
Ring-2_min = Ring-1 + CARD_H + margin
           = 310   + 200    + 30
           = 540px
```
当前 Ring-2=540px，恰好满足父子不重叠条件（ΔR=230 > CARD_H=200）。不要减小。

### 3.3 Wheel 事件必须用 imperative listener

React 合成事件默认 passive，无法 `preventDefault()`。必须：
```typescript
useEffect(() => {
  el.addEventListener('wheel', onWheel, { passive: false })
  return () => el.removeEventListener('wheel', onWheel)
}, [])
```

### 3.4 Toolbar 必须在 canvas-layer 外

任何固定 HUD 元素（工具栏、角落控件、EventsPanel）都不能放在 `.canvas-layer` 内，否则会随 pan/zoom 移动。EventsPanel 使用 `position: fixed`，脱离所有 canvas 层级。

### 3.5 MiniMax API 必须含 `/v1`

```
base_url: https://api.minimaxi.com/v1   ← 正确（无末尾斜杠）
base_url: https://api.minimaxi.com      ← 错误，会 404
```

### 3.6 api_key 不回传前端

settings API 只返回 `{configured: bool}`，前端不展示密钥明文。

---

## 4. 已知问题 & 待处理

| 问题 | 严重程度 | 建议处理 |
|------|----------|---------|
| Ring-2 节点部分超出 canvas 边界 | 低 | 设计预期（canvas 可平移）；如需完整显示可扩展 canvas-layer 到 1600×1200 |
| orbit.two CSS 与 Ring-2 半径不一致 | 低 | orbit.two 应为 1080px（540×2），目前 760px，仅影响装饰圆环视觉 |
| 拖拽后刷新位置重置 | 低 | localStorage 缓存 dragOverrides，key 按 session_id |
| SSE Streaming 未实现 | 高 | 见 Section 5 |
| confidence 在 per_agent_status 为 0 | 低 | per_agent_status 无 confidence 字段，需从 perspective_detail 取 |

---

## 5. 下一步开发优先级

### 🔥 P0 — 信息层基础建设（刚刚讨论）

**背景**：用户第一次打开产品没有数据 → Agent 输出空洞 → 立即放弃。

**方案：三层架构 + 三个内置 Agent**

```
Layer 0: 数据入口
  ├── 内置免费数据源（yfinance + FRED + SEC EDGAR）← 解决冷启动，$0 成本
  ├── 用户自定义 API 接入
  └── 客户私有数据（Excel / CSV / Markdown）

Layer 1: Agent 接入层
  ├── Agent A: Connector Copilot — 读 API 文档 → connector_spec.yaml
  ├── Agent B: Canonical Mapping Agent — 外部字段 → PYTA canonical schema
  └── Agent C: Data Quality Validator — quality_score，质量不足降级推演

Layer 2: Canonical Data Store
  CanonicalSecurityData { symbol, market, price, fundamentals, sentiment, events, raw_payload }
  推演 Agent 只消费这层，不直接碰原始 API
```

**立即可做（本周）**：
1. 接入 yfinance（$0，NVDA 数据立即可用）→ canonical schema 打通
2. 推演 Agent 消费 canonical data 替代硬编码 mock

**下一步**：
3. Connector Copilot UI（用户粘贴 API 文档 URL）
4. Excel/Markdown 上传 Agent（客户私有数据）

**待决策**：yfinance 是爬 Yahoo Finance，商业化有合规风险。若在意，改用 Alpha Vantage 免费 tier（25次/天）。

---

### P1 — SSE Streaming（改变体验）

推演中 Agent 卡逐个出现，不等全部完成。

**后端**：新增 `POST /api/v1/sandbox/stream`
```python
async def run_streaming(self, request):
    for coro in asyncio.as_completed(tasks):
        result = await coro
        yield f"data: {result.json()}\n\n"
```

**前端**：`useSandboxRun` 改 EventSource；Agent 卡按完成顺序淡入；显示「已完成 3/5」进度。

---

### P2 — 场景参数持久化

CenterCoreCard 的 ticker/market/narrative 改动目前仅存 React state，刷新即丢失。需要：
- `POST /api/v1/session/scene` 保存场景参数
- `GET /api/v1/session/scene` 恢复

---

### P3 — orbit.two CSS 修正

```css
/* 当前（错误）: */
.orbit.two { width: 760px; height: 760px; }
/* 应为（Ring-2 直径 = 540×2）: */
.orbit.two { width: 1080px; height: 1080px; }
```

---

## 6. 项目文件速查

```
# Backend
src/api/app.py                           FastAPI 入口
src/api/routers/sandbox.py               POST /sandbox/run
src/api/routers/user_settings.py         用户设置 API
src/sandbox/agents/runner.py             asyncio.gather 并发 5 Agent
src/sandbox/agents/templates/            Agent prompt 模板
src/sandbox/llm/client.py               LLM 调用（timeout=60s，think标签剥离）
src/sources/catalog.json                 Provider 配置
src/sources/adapter.py                   数据源适配器
src/config/settings.py                   全局配置

# Frontend — Layer 1（信息面板）
frontend/src/components/layout/InformationPanel.tsx
frontend/src/components/layout/AddSourceModal.tsx
frontend/src/components/layout/SettingsPopover.tsx
frontend/src/components/canvas/EventChips.tsx     ← 数据获取保留，UI 已移入 EventsPanel

# Frontend — Layer 2（画布）
frontend/src/components/layout/CanvasStage.tsx          主画布（三区 + EventsPanel 状态）
frontend/src/components/layout/CommandConsole.tsx        控制台（时间轴 + 事件chip + 推演按钮）
frontend/src/components/layout/EventsPanel.tsx           Layer 3 右侧事件面板（NEW）
frontend/src/components/canvas/AgentNode.tsx             Agent 节点（ring class + 拖拽）
frontend/src/components/canvas/EdgeLayer.tsx             SVG 边（spoke/peer/derivation/synthesis）
frontend/src/components/canvas/CenterCoreCard.tsx        中心可编辑卡片
frontend/src/components/canvas/CanvasBackground.tsx      点阵背景
frontend/src/hooks/useCanvasViewport.ts                  pan + zoom
frontend/src/hooks/useTopologyLayout.ts                  同心环拓扑算法（NEW）
frontend/src/hooks/useSandboxRun.ts                      推演状态 + 多轮 + ring-2 子节点生成
frontend/src/lib/types/canvas.ts                         全部类型
frontend/src/lib/mock/canvasState.ts                     Mock 状态（初始 ring-1 坐标）
frontend/src/styles/research-canvas.css                  全部 UI 样式
```

---

## 7. 快速启动

```bash
git clone https://github.com/justicengg/pyta-research
git checkout main   # 今日已 merge

# Backend
poetry install
poetry run uvicorn src.api.app:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# 配置 LLM（一次性）
curl -X POST http://localhost:8000/api/v1/settings/llm \
  -H 'Content-Type: application/json' \
  -d '{"base_url":"https://api.minimaxi.com/v1","model":"MiniMax-M2.7","api_key":"YOUR_KEY"}'

# 测试推演（NVDA，预期 ~28s 返回 complete）
python3 -c "
import asyncio, httpx, datetime
async def t():
    r = await httpx.AsyncClient(timeout=120).post(
        'http://localhost:8000/api/v1/sandbox/run',
        json={'ticker':'NVDA','market':'US',
              'events':[{'event_id':'t1','event_type':'manual_input',
                         'content':'英伟达算力订单增长，台积电产能受限','source':'cli',
                         'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'symbol':'NVDA','metadata':{}}],
              'round_timeout_ms':90000,'narrative_guide':'NVDA 2026Q1 推演'})
    print(r.json()['round_complete']['data_quality'])
asyncio.run(t())
"
```

---

## 8. 设计原则（勿破坏）

1. **不带回旧世界** — buy/sell/hold、target price、portfolio simulation 一律不出现
2. **核心场景在中心** — center-core 是锚点，Agent 围绕同心环运转
3. **TOPOLOGY_CENTER 与 CSS 必须对齐** — `top: 50%` = y:450，不要改
4. **Ring-2 ≥ 540px** — 否则父子节点重叠（推导：R1+CARD_H+30=540）
5. **wheel listener 必须 passive: false** — React 合成事件无法 preventDefault
6. **任何 HUD 不能放 canvas-layer 内** — 否则随 pan/zoom 移动
7. **MiniMax base_url 必须含 `/v1`** — `https://api.minimaxi.com/v1`
8. **api_key 不回传前端** — 只返回 `{configured: bool}`

---

*文档由 Claude Sonnet 4.6 更新于 2026-03-22，反映今日 PR #69 merge 后的完整代码状态。*
