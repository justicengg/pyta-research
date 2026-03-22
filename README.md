# PYTA Research — Secondary Market MVP

多 Agent 二级市场沙盘推演系统。用户输入市场事件，5 个市场参与者 Agent 围绕事件并发推演，输出各自视角的观察、关注点与分析焦点。

---

## 当前分支

```
PYTA/secondary-market-mvp
```

## Tech Stack

| 层 | 技术 |
|----|------|
| Backend | Python 3.11 · FastAPI · SQLAlchemy · SQLite · httpx |
| LLM | OpenAI-compatible API（默认 MiniMax-M2.7，支持任意兼容模型） |
| Frontend | Vite · React · TypeScript |
| 数据库 | SQLite（`pyta.db`） |

---

## Quick Start

### 1. Backend

```bash
poetry install
poetry run uvicorn src.api.app:app --reload --port 8000
```

访问 `http://localhost:8000/health` 确认启动。

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:4174`

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
| `POST /api/v1/sandbox/run` | 触发沙盘推演（5 Agent 并发） |
| `GET /api/v1/sources/catalog` | 可接入的数据源列表 |
| `GET /api/v1/sources/connectors` | 已接入数据源 |
| `POST /api/v1/sources/connectors` | 接入新数据源 |
| `GET /api/v1/sources/events?limit=5` | 最新事件（来自已接入来源） |
| `GET /api/v1/settings/llm/status` | LLM 配置状态 |
| `POST /api/v1/settings/llm` | 保存 LLM 配置 |

---

## 5 个市场参与者 Agent

| Agent | 视角 |
|-------|------|
| `traditional_institution` | 传统机构 — 重估值、仓位与中长期配置 |
| `quant_institution` | 量化机构 — 规则、信号与微观结构 |
| `retail` | 普通散户 — 热点、叙事与情绪 |
| `offshore_capital` | 海外资金 — 全球流动性与风险偏好 |
| `short_term_capital` | 游资/短线 — 题材热度与事件驱动 |

---

## 项目结构

```
src/
├── api/
│   ├── app.py                        # FastAPI 主入口，只注册 sandbox / sources / settings
│   ├── routers/
│   │   ├── sandbox.py                # 沙盘推演路由
│   │   ├── sources.py                # 数据源接入路由
│   │   └── user_settings.py          # LLM 配置路由
│   └── settings_store.py             # SQLite KV 存储（user_settings 表）
├── sandbox/
│   ├── agents/
│   │   ├── runner.py                 # 并发 Agent 执行器（asyncio.gather）
│   │   └── templates/
│   │       └── secondary_prompts.py  # 5 个 Agent Prompt 模板
│   ├── llm/
│   │   └── client.py                 # OpenAI-compatible 客户端，自动剥离 <think> 标签
│   └── schemas/                      # Agent / Event / Report 数据结构
├── sources/
│   ├── catalog.json                  # Provider 配置（config-driven，加新来源只改此文件）
│   ├── adapter.py                    # 通用连接验证器（支持 query_param / bearer / x_api_key）
│   └── store.py                      # source_connector / source_event DB 操作
└── db/
    ├── base.py
    └── models.py                     # SQLAlchemy ORM 模型

frontend/src/
├── components/
│   ├── canvas/
│   │   ├── AgentNode.tsx             # Agent 卡片节点
│   │   ├── AgentResultCard.tsx       # 推演结果卡
│   │   └── EventChips.tsx            # 事件 chips（点击自动填入控制台）
│   └── layout/
│       ├── InformationPanel.tsx      # 左侧信息层 Layer 1（收起 = 28px rail）
│       ├── CanvasStage.tsx           # 沙盘画布 Layer 2
│       ├── CommandConsole.tsx        # 底部控制台（触发 sandbox run）
│       ├── AddSourceModal.tsx        # 接入新来源 Modal（支持 catalog + custom）
│       └── SettingsPopover.tsx       # ⚙ 设置（主题 + LLM API Key）
├── hooks/
│   └── useSandboxRun.ts              # 沙盘调用 hook（timeout 60s）
└── lib/
    ├── api/                          # API 调用层
    ├── adapters/sandboxAdapter.ts    # 后端响应 → 前端 canvas state 映射
    └── types/                        # TypeScript 类型定义
```

---

## 重要注意事项

- **LLM 推理超时**：默认 60s/agent，MiniMax-M2.7 等推理模型输出 `<think>` 标签，系统自动剥离
- **GNews 免费额度**：100 次/天，接入时自动拉取 10 条初始事件存入 `source_event` 表
- **Custom Source**：支持任意 REST API（填写 base_url + auth style + api key）
- **旧世界代码**：已归档至 `docs/archive/legacy_world/`，不影响当前系统运行

---

## 开发文档

| 文档 | 说明 |
|------|------|
| `docs/SECONDARY_MARKET_BRANCH_HANDOFF.md` | 当前分支完整交接文档（source of truth） |
| `docs/LAYER2_ROADMAP.md` | Layer 2 沙盘画布开发路线图 |
| `docs/RESEARCH_CANVAS_DESIGN_SPEC.md` | UI 设计规范 |
| `docs/archive/legacy_world/` | 旧世界归档代码（只读参考） |
