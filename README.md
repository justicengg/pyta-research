# PYTA Research

多市场 AI 研究沙盘系统。支持一级市场深推演与二级市场多 Agent 并行沙盘两种分析模式。

---

## 当前分支

```
main                        ← 主分支
feat/primary-market-mvp     ← 一级市场模块开发（当前活跃）
PYTA/secondary-market-mvp   ← 二级市场模块开发（当前活跃）
```

---

## Tech Stack

| 层 | 技术 |
|----|------|
| Backend | Python 3.11 · FastAPI · SQLAlchemy · SQLite · Alembic |
| LLM | OpenAI-compatible API（默认 MiniMax-M2.7，支持任意兼容模型） |
| Frontend | Vite · React · TypeScript |
| 数据库 | SQLite（`pyta.db`） |

---

## 两种分析模式

### 一级市场深推演（Primary Market）

针对早期投资决策的深度推演系统，多轮串行收敛，输出结构化投资判断。

**四模块分析框架：**

| 模块 | 说明 |
|------|------|
| 不确定性地图 | 6 个维度评估市场风险（市场成立性、技术壁垒、团队执行力、商业化路径、竞争格局、烧钱周期） |
| 创始人分析 | 四层结构：公司阶段 × 创始人原型 × 阶段匹配度 × 执行信号 |
| 关键假设 | 硬假设 / 软假设分类管理，自动验证 LTV/CAC 和 Runway |
| 财务透视 | ARR、NRR、毛利率、月烧钱、LTV/CAC、估值、Runway |

**路径分叉（PathFork）：** 当硬假设被违反时自动生成，展示"假设成立 vs 假设失效"两条路径及推荐行动。

**三门停止机制：**
- `convergence`：平均置信度 ≥ 0.85
- `max_rounds`：达到最大轮次（默认 3 轮）
- `oscillation`：连续 N 轮 delta < 0.02

---

### 二级市场并行沙盘（Secondary Market）

用户输入市场事件，5 个市场参与者 Agent 并发推演，输出各自视角的分析与博弈结果。

**5 个市场参与者 Agent：**

| Agent | 视角 |
|-------|------|
| `traditional_institution` | 传统机构 — 重估值、仓位与中长期配置 |
| `quant_institution` | 量化机构 — 规则、信号与微观结构 |
| `retail` | 普通散户 — 热点、叙事与情绪 |
| `offshore_capital` | 海外资金 — 全球流动性与风险偏好 |
| `short_term_capital` | 游资 / 短线 — 题材热度与事件驱动 |

**Interaction Resolution：** 5 个 Agent 推演完成后，自动生成市场力量博弈面板（多空压力、主导力量、强化 / 冲突关系）。

---

## Quick Start

### 1. Backend

```bash
poetry install
poetry run alembic upgrade head   # 建表（生产环境走 migration）
poetry run uvicorn src.api.app:app --reload --port 8000
```

> ⚠️ **MVP 开发阶段**如果没有 Alembic migration，可临时用以下方式建表：
> ```python
> from src.db.base import Base
> from src.db import models
> from src.db.session import engine
> Base.metadata.create_all(engine)
> ```
> 生产部署前必须接入 Alembic migration。

访问 `http://localhost:8000/health` 确认启动。

### 2. Frontend

```bash
cd frontend
npm install
npm run dev -- --port 5174   # 一级市场 MVP
# 或
npm run dev                   # 二级市场 MVP（默认 5173）
```

### 3. 配置 LLM API Key

进入前端 → 左侧边栏 ⚙ 设置 → 填入：

- **Base URL**：`https://api.minimaxi.com/v1`（必须包含 `/v1`）
- **Model**：`MiniMax-M2.7`
- **API Key**：你的 MiniMax API Key

Key 存储在 `pyta.db` 的 `user_settings` 表，不暴露给前端。

---

## 核心 API 端点

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `POST /api/v1/primary/run` | 触发一级市场深推演（多轮收敛） |
| `GET /api/v1/primary/{sandbox_id}/result` | 获取一级市场推演结果 |
| `POST /api/v1/sandbox/run` | 触发二级市场沙盘推演（5 Agent 并发） |
| `GET /api/v1/sources/catalog` | 可接入的数据源列表 |
| `POST /api/v1/sources/connectors` | 接入新数据源 |
| `GET /api/v1/sources/events?limit=5` | 最新事件（来自已接入来源） |
| `POST /api/v1/upload` | 上传文件作为分析上下文 |
| `GET /api/v1/settings/llm/status` | LLM 配置状态 |
| `POST /api/v1/settings/llm` | 保存 LLM 配置 |

---

## 项目结构

```
src/
├── api/
│   ├── app.py                          # FastAPI 主入口
│   ├── deps.py                         # API Key 鉴权
│   └── routers/
│       ├── primary.py                  # 一级市场推演路由
│       ├── sandbox.py                  # 二级市场沙盘路由
│       ├── sources.py                  # 数据源接入路由
│       ├── upload.py                   # 文件上传路由
│       ├── market.py                   # 市场快照路由
│       └── user_settings.py            # LLM 配置路由
├── sandbox/
│   ├── orchestrator/
│   │   ├── primary.py                  # 一级市场编排器（多轮串行收敛）
│   │   └── secondary.py                # 二级市场编排器（单轮并发 fan-out）
│   ├── schemas/
│   │   ├── primary_market.py           # 一级市场数据结构（四模块 + PathFork）
│   │   ├── agents.py                   # Agent 输出结构
│   │   ├── reports.py                  # 推演报告结构
│   │   └── events.py                   # 事件结构
│   ├── services/
│   │   ├── assumption_checker.py       # 自动验证硬假设（LTV/CAC、Runway）
│   │   ├── path_fork.py                # PathFork 生成服务
│   │   ├── interaction_resolver.py     # 二级市场博弈解析
│   │   └── synthesis.py                # 推演结果综合
│   └── llm/
│       └── client.py                   # OpenAI-compatible 客户端，自动剥离 <think>
├── db/
│   ├── base.py
│   ├── models.py                       # SQLAlchemy ORM 模型
│   └── session.py
└── config/
    └── settings.py                     # 环境变量配置

frontend/src/
├── pages/
│   └── ResearchCanvasPage.tsx          # 顶层路由：模式选择 → primary / secondary
├── components/
│   ├── canvas/
│   │   ├── primary/                    # 一级市场四模块卡片
│   │   │   ├── PrimaryCanvasLayout.tsx
│   │   │   ├── UncertaintyMapCard.tsx
│   │   │   ├── FounderAnalysisCard.tsx
│   │   │   ├── KeyAssumptionsCard.tsx
│   │   │   ├── FinancialLensCard.tsx
│   │   │   └── PathForkCard.tsx
│   │   ├── AgentNode.tsx               # 二级市场 Agent 卡片
│   │   ├── EnvironmentFlowLayer.tsx    # 信号流动画层
│   │   └── InteractionFlowLayer.tsx    # 博弈关系动画层
│   ├── environment/
│   │   └── EnvironmentBar.tsx          # 二级市场环境信号横条
│   └── layout/
│       ├── MarketModeSelector.tsx      # 模式选择入口
│       ├── CanvasStage.tsx             # 画布主舞台（pan / zoom）
│       ├── CommandConsole.tsx          # 二级市场命令终端
│       ├── PrimaryCommandConsole.tsx   # 一级市场命令终端
│       ├── InformationPanel.tsx        # 左侧信息层（二级市场）
│       ├── AddSourceModal.tsx          # 接入新来源 Modal
│       ├── UploadModal.tsx             # 文件上传 Modal
│       └── ConnectorCopilotModal.tsx   # 智能接入助手 Modal
├── hooks/
│   ├── usePrimaryRun.ts                # 一级市场推演状态管理
│   ├── useSandboxRun.ts                # 二级市场推演状态管理
│   └── useCanvasViewport.ts            # 画布 pan / zoom
└── lib/
    ├── api/
    │   └── primary.ts                  # 一级市场 API 调用层
    ├── types/
    │   ├── primaryCanvas.ts            # 一级市场前端类型
    │   └── canvas.ts                   # 二级市场前端类型
    └── mock/
        └── primaryCanvasState.ts       # 一级市场默认展示数据
```

---

## 注意事项

- **LLM 推理超时**：默认 60s/agent，MiniMax-M2.7 等推理模型输出 `<think>` 标签，系统自动剥离
- **一级 / 二级模式独立**：两个模式的命令终端、画布布局、数据结构完全分离，MVP 阶段不合并
- **PathFork 仅在运行后出现**：默认状态不显示路径分叉，只有硬假设被违反后才生成
- **GNews 免费额度**：100 次/天，接入时自动拉取 10 条初始事件

---

## 开发文档

| 文档 | 说明 |
|------|------|
| `docs/BRANCH_CONFLICT_PLAYBOOK.md` | Worktree 多分支合并规则（高风险文件、合并顺序、冲突处理）|
| `docs/RESEARCH_CANVAS_DESIGN_SPEC.md` | UI 设计规范 |
| `docs/LAYER2_ROADMAP.md` | 画布层开发路线图 |
| `CLAUDE.md` | Claude Code 工作指令 |
| `AGENTS.md` | Codex / 其他 Agent 工作指令 |
