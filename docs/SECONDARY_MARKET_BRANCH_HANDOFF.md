# Secondary Market MVP — Branch Handoff

> **Last updated**: 2026-03-22
> **Branch**: `PYTA/secondary-market-mvp`
> **Status**: Layer 1 complete · Layer 2 in roadmap

---

## 1. 当前系统状态

### ✅ 已完成

#### Backend
- FastAPI 主链路（`src/api/app.py`）— 只注册 sandbox / sources / settings 三个 router
- 沙盘推演：`POST /api/v1/sandbox/run` — 5 个 Agent 并发，MiniMax live 联调已验证（5/5 通过）
- LLM Client（`src/sandbox/llm/client.py`）：
  - OpenAI-compatible，支持任意兼容模型
  - 自动剥离推理模型 `<think>...</think>` 标签（MiniMax-M2.7 必需）
  - DB 配置优先于 .env，运行时可切换，无需重启
- 数据源接入（`src/sources/`）：
  - Config-driven catalog（catalog.json）— 加新 provider 只改 JSON
  - 通用 adapter：query_param / bearer / x_api_key 三种 auth
  - Custom Source：用户自定义任意 REST API
  - 接入时自动拉取初始事件（GNews 已验证）
- LLM 配置：key 不回传前端，只返回 configured 状态

#### Frontend Layer 1
- 左侧信息层（InformationPanel.tsx）：Sources、Recommended、Session、External Agent
- 收起态：28px rail，不占 canvas 空间
- 设置面板（SettingsPopover.tsx）：主题 + LLM 配置，Portal 渲染
- 数据源接入 Modal（AddSourceModal.tsx）：catalog + custom source，带验证
- EventChips（EventChips.tsx）：CommandConsole 正上方，点击填入控制台
- 全局布局：flat panel layout，单线分割，无 gap 无圆角

#### 旧世界清理
- 旧 router / 业务模块 / 测试全部归档至 docs/archive/legacy_world/
- CI 已通过

---

## 2. 架构说明

### 数据库（SQLite — pyta.db）

| 表 | 用途 |
|----|------|
| user_settings | KV 存储，LLM api_key / base_url / model |
| source_connector | 已接入数据源（api_key 明文，MVP） |
| source_event | 标准化事件 |
| sandbox_sessions | 每次推演 session |
| agent_snapshots | Agent 推演快照 |
| report_records | 推演报告 |

### LLM 配置优先级
DB (user_settings) > .env > 代码默认值

### Source Provider 扩展
只需在 src/sources/catalog.json 加一条记录，无需改代码。

---

## 3. 已知问题

| 问题 | 状态 |
|------|------|
| MiniMax base_url 必须含 /v1 | ✅ 已修复，默认值已更正 |
| 推理模型 think 标签干扰解析 | ✅ 已修复，client.py 自动剥离 |
| Agent timeout | ✅ 60s，前后端同步 |
| GNews 返回通用新闻 | ⚠️ free tier 限制，Finnhub 后改善 |
| api_key 明文存储 | ⚠️ MVP 临时，生产需加密 |
| Canvas Agent 卡片重叠 | 🔴 Layer 2 修复 |
| Canvas Toolbar 无用按钮 | 🔴 Layer 2 清理 |

---

## 4. 启动开发环境

```bash
# Backend
poetry run uvicorn src.api.app:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# 验证
curl http://localhost:8000/health
```

---

## 5. 关键文件

```
src/api/app.py                                    FastAPI 入口
src/api/routers/sandbox.py                        SandboxRunRequest（timeout 60s）
src/api/routers/sources.py                        Source CRUD + event 拉取
src/sandbox/agents/runner.py                      asyncio.gather 并发
src/sandbox/agents/templates/secondary_prompts.py 5个Agent prompt
src/sandbox/llm/client.py                         LLM调用 + think剥离
src/sources/catalog.json                          Provider配置（唯一扩展入口）
frontend/src/hooks/useSandboxRun.ts               前端触发沙盘
frontend/src/components/layout/CanvasStage.tsx    Layer 2主画布（待重构）
frontend/src/components/layout/InformationPanel.tsx Layer 1信息层
frontend/src/components/canvas/EventChips.tsx     事件chips
```

---

## 6. 下一步：Layer 2

详见 docs/LAYER2_ROADMAP.md
