# 框架总览 (FRAMEWORK)

> 本文档随框架演进持续更新，不在代码中固化任何规则——所有决策准则、评分标准、策略参数均以当前版本文档为准。

## 目标

PYTA 是一个多 agent 协同的二级市场研究框架，目标是通过分层分工将信息收集、策略分析、最终决策三个环节结构化，提升投研效率和决策质量。

## 分层架构

```
┌─────────────────────────────────────────────┐
│              大善人（总监）                    │
│   最终决策 / 质量控制 / 框架演进               │
├─────────────────────────────────────────────┤
│              大呆子（策略官）                  │
│   策略卡生成 / 执行跟踪 / 交易计划             │
├─────────────────────────────────────────────┤
│              大聪明（信息官）                  │
│   数据拉取 / 市场扫描 / 候选初筛               │
├─────────────────────────────────────────────┤
│              数据管道（Phase 1）               │
│  raw_price / raw_fundamental / raw_macro     │
└─────────────────────────────────────────────┘
```

## Agent 角色

### 大聪明（信息官）
- 负责范围：市场数据拉取、基本面数据采集、宏观数据跟踪、候选标的初筛
- 输出：结构化数据报告、候选池列表
- 工具：数据管道 CLI、质量检查报告

### 大呆子（策略官）
- 负责范围：策略卡制定、仓位计划、执行追踪、止损止盈管理
- 输出：策略卡（格式见当前版本文档，不在代码中固化）、执行日志
- 工具：策略层模块（Phase 2）

### 大善人（总监）
- 负责范围：最终进出场决策、框架规则制定与修订、整体质量把控
- 输出：决策记录、框架版本迭代
- 决策准则：**见当前版本 FRAMEWORK.md，不在代码中硬编码，随时可修改**

## 开发阶段

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1 | 数据管道 MVP（价格/基本面/宏观采集、质量检查、调度） | 完成 |
| Phase 2 | 策略层（信号计算、策略卡、大呆子模块） | 待开发 |
| Phase 3 | 决策层（大善人模块、风控、报告推送） | 待开发 |

## 数据流

```
外部数据源
  baostock (CN价格/基本面)
  yfinance  (US价格)
  FRED API  (宏观)
       |
       v
  DataFetcher（增量拉取 + 去重）
       |
       v
  PostgreSQL raw_* 表
  （quality_status: pending -> passed/flagged）
       |
       v
  DataQualityChecker（规则引擎）
       |
       v
  [Phase 2] 信号 / 因子计算
       |
       v
  [Phase 2] 策略卡 -> 大呆子
       |
       v
  [Phase 3] 最终决策 -> 大善人
```

## 关键设计原则

1. **Point-in-Time**：基本面数据以 publish_date 为准，避免未来数据泄漏
2. **Adapter 注入**：所有 fetcher 支持测试时注入 mock adapter，生产走 default
3. **配置驱动**：watchlist（标的池、宏观序列）通过 .env 配置，不写死在代码里
4. **规则外置**：策略规则、决策准则记录在文档中，便于随时调整，不硬编码

---

## 策略卡规范（大呆子 — 策略官）

> 规则随实践演进，以下为当前版本，所有参数均可通过 `.env` 调整，无需改代码。

### strategy_card 字段说明

| 字段 | 类型 | 填写方式 | 说明 |
|------|------|----------|------|
| symbol | VARCHAR(32) | 自动 | 标的代码 |
| market | VARCHAR(16) | 自动 | 市场（CN/US） |
| valuation_note | TEXT | 自动 | 因子快照（ROE/负债率/动量等） |
| entry_price | NUMERIC | 自动 | 进场参考价（asof_date 收盘价） |
| entry_date | DATE | 自动 | 建议进场日期 |
| stop_loss_price | NUMERIC | 自动 | 止损价（见止损规则） |
| thesis | TEXT | **人工** | 赚什么钱？催化剂？ |
| position_pct | NUMERIC | **人工** | 目标仓位占比（如 0.05 = 5%） |
| status | VARCHAR | 系统 | draft → active → closed |
| close_reason | TEXT | 人工/系统 | 平仓原因 |

### 止损规则（当前版本）

通过 `.env` 设置 `STRATEGY_STOP_LOSS_METHOD`：

| 方法 | 参数 | 公式 |
|------|------|------|
| `pct`（默认） | `STRATEGY_STOP_LOSS_PCT=0.08` | stop = entry × (1 - 0.08) |
| `atr` | `STRATEGY_STOP_LOSS_ATR_WINDOW=14`<br>`STRATEGY_STOP_LOSS_ATR_MULTIPLIER=2.0` | stop = entry − 2.0 × ATR(14) |

ATR = Average True Range，TR = max(High-Low, \|High-PrevClose\|, \|Low-PrevClose\|)

### 筛选规则（当前版本）

通过 `.env` 设置 `SCREENER_RULES`（JSON 数组，格式 `factor:op:threshold`）：

| 因子 | 规则 | 含义 |
|------|------|------|
| roe_latest | >= 0.08 | ROE 不低于 8% |
| momentum_20d | >= 0.0 | 20 日正动量 |
| debt_ratio_latest | <= 0.70 | 负债率不超过 70% |
| volume_ratio_5_20 | >= 0.80 | 量能不萎缩 |

> 以上仅为初始默认值，可随时在 `.env` 中修改，无需改代码。大善人可在复盘后调整阈值。
