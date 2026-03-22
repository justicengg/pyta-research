# 使用指南 (USAGE)

## 环境准备

```bash
# 安装依赖
pip install poetry
poetry install

# 配置环境变量（复制模板后按需修改）
cp .env.example .env
```

`.env` 关键配置项：

```ini
# 数据库（默认 SQLite，生产换 PostgreSQL）
DATABASE_URL=sqlite:///./pyta.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/pyta

# FRED API Key（US宏观数据，免费申请）
FRED_API_KEY=your_key_here

# 调度时间（默认每天 18:00 上海时间）
SCHEDULER_CRON_HOUR=18
SCHEDULER_CRON_MINUTE=0

# 标的池（JSON数组格式，随时修改无需改代码）
PIPELINE_CN_SYMBOLS=["sh.600000"]
PIPELINE_US_SYMBOLS=["SPY"]
PIPELINE_CN_FUNDAMENTAL_SYMBOLS=["600000"]
PIPELINE_MACRO_SERIES=["CPIAUCSL:US:fred","UNRATE:US:fred"]
```

## 数据库初始化

```bash
alembic upgrade head
```

## CLI 命令

### 拉取行情数据

```bash
# A股（baostock）
python -m src.cli fetch market --source baostock --symbol sh.600000 --market CN \
  --start 2025-01-01 --end 2025-12-31 --incremental

# 美股（yfinance）
python -m src.cli fetch market --source yfinance --symbol SPY --market US \
  --start 2025-01-01 --end 2025-12-31 --incremental
```

### 拉取基本面数据

```bash
# asof = 截止日期（Point-in-Time 过滤，只取 publish_date <= asof 的数据）
python -m src.cli fetch fundamental --symbol 600000 --market CN \
  --asof 2025-12-31 --incremental
```

### 拉取宏观数据

```bash
# US CPI（FRED）
python -m src.cli fetch macro --series CPIAUCSL --source fred --market US \
  --start 2020-01-01 --end 2025-12-31 --incremental

# 失业率
python -m src.cli fetch macro --series UNRATE --source fred --market US \
  --start 2020-01-01 --end 2025-12-31 --incremental
```

### 数据质量检查

```bash
# 输出 JSON 质量报告
python -m src.cli quality check --table raw_price --date 2025-12-31 --out /tmp/report.json
python -m src.cli quality check --table raw_fundamental --date 2025-12-31 --out /tmp/report.json
python -m src.cli quality check --table raw_macro --date 2025-12-31 --out /tmp/report.json
```

### 调度器

```bash
# 手动触发一次完整管道（拉取 + 质量检查）
python -m src.cli scheduler run-once

# 启动定时调度（按 .env 中的 SCHEDULER_CRON_HOUR/MINUTE 运行）
python -m src.cli scheduler start
```

## 扩展标的池

不需要改代码，直接修改 `.env`：

```ini
PIPELINE_CN_SYMBOLS=["sh.600000","sh.000001","sh.600036"]
PIPELINE_US_SYMBOLS=["SPY","QQQ","AAPL"]
PIPELINE_CN_FUNDAMENTAL_SYMBOLS=["600000","000001","600036"]
PIPELINE_MACRO_SERIES=["CPIAUCSL:US:fred","UNRATE:US:fred","DGS10:US:fred"]
```

重启调度器后生效。

## 运行测试

```bash
pytest tests/ -v
```
