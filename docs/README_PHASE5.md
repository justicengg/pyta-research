# Phase 5 更新说明与使用指南

本文说明 INV-48 ~ INV-53 的更新范围，以及如何在 API 与 Dashboard 中使用新能力。

## 1. 更新了什么

## 1.1 数据模型与迁移
- `strategy_card` 新增 StrategyCard 2.0 字段：
  - `industry`, `expected_cycle`, `valuation_anchor`, `position_rules`,
    `entry_rules`, `exit_rules`, `risk_rules`, `review_cadence`, `rules_version`
- 新增两张核心表：
  - `action_queue`：系统建议队列（含状态、优先级、规则标签）
  - `execution_log`：执行审计日志（系统建议响应 + 手动交易）
- 新增约束：
  - `execution_log.action_queue_id ON DELETE SET NULL`
  - action queue 业务唯一键（避免同日重复建议）
  - 复合索引 `(generated_date, status, priority)`

## 1.2 API 增强
- 卡片增强：
  - `PATCH /api/v1/cards/{id}` 支持 StrategyCard 2.0 字段
  - JSON 规则字段语义为“整体替换”，不做 merge
  - 状态机校验：非法迁移返回 400
  - `GET /api/v1/cards/{id}/history` 支持分页与时间过滤
- 新增队列与执行 API：
  - `GET /api/v1/actions`
  - `GET /api/v1/actions/today`
  - `GET /api/v1/actions/{id}`
  - `POST /api/v1/actions/{id}/respond`
  - `GET /api/v1/executions`
  - `POST /api/v1/executions`
  - `GET /api/v1/executions/{id}`

## 1.3 规则引擎升级
- 保留原有 `evaluate()`（给 `/api/v1/decision/evaluate` 使用）
- 新增 `generate_queue(asof, session)`：
  - 生成并持久化 `action_queue`
  - 同日重跑幂等（不重复插入）
  - 过期昨日 `pending` 建议为 `expired`
- 调度新增队列步骤：`_run_queue()`

## 1.4 Dashboard 2.0
- 页面升级为三 Tab：`观察 / 决策 / 执行`
- 新增服务端写代理接口（前端不接触 API Key）：
  - `POST /dashboard/login`
  - `POST /dashboard/respond`
  - `POST /dashboard/executions`
- 安全控制：
  - 写操作会话鉴权（dashboard token 登录态）
  - CSRF（双提交 token）
  - Origin/Referer 同源校验
  - 写操作审计信息（operator/request_id/source_ip）入库

## 2. 如何使用

## 2.1 升级数据库
```bash
alembic upgrade head
```

## 2.2 启动服务
```bash
python -m src.cli api start
```

## 2.3 调度生成建议队列
```bash
python -m src.cli scheduler run-once
```

执行后可查询：
```bash
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/api/v1/actions/today
```

## 2.4 卡片规则更新（示例）
```bash
curl -X PATCH "http://127.0.0.1:8000/api/v1/cards/1" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "review_cadence":"monthly",
    "valuation_anchor":{"core_metric":"price","fair_low":10,"fair_high":15},
    "entry_rules":{"trigger_conditions":["valuation_below_fair_low"],"filter_conditions":["always_true"]},
    "risk_rules":{"stock_max_loss_pct":0.15}
  }'
```

## 2.5 Dashboard 写操作流程
1. 打开 `/dashboard`
2. 在“决策”页使用 `Dashboard Token` 登录写权限
3. 执行“接受/拒绝/修改”建议，或在“执行”页手动录入执行

## 3. 生产配置新增项

在 `.env`（或 systemd EnvironmentFile）中新增：
```bash
API_KEY=<your_api_key>
DASHBOARD_WRITE_TOKEN=<strong_random_token>
```

说明：
- `API_KEY` 保护 `/api/v1/*`
- `DASHBOARD_WRITE_TOKEN` 仅用于 Dashboard 写操作登录，不会注入 HTML

## 4. 变更文件索引

- 模型与迁移：
  - `src/db/models.py`
  - `alembic/versions/20260305_0005_strategy_card_v2_fields.py`
  - `alembic/versions/20260305_0006_add_action_queue_execution_log.py`
- API：
  - `src/api/routers/cards.py`
  - `src/api/routers/actions.py`
  - `src/api/routers/executions.py`
  - `src/api/routers/dashboard.py`
- 调度与规则：
  - `src/decision/advisor.py`
  - `src/scheduler/scheduler.py`
- 前端模板：
  - `src/api/templates/dashboard.html`
