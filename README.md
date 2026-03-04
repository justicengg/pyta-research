# pyta-research

PYTA Investment Framework 实现仓库（当前已覆盖 Phase 1 ~ Phase 5 核心能力）。

## Scope
- Phase 1: 数据采集、质量检查、调度
- Phase 2-4: API 服务与基础 Dashboard
- Phase 5:
  - Strategy Card 2.0（规则字段、校验、状态机）
  - Action Queue + Execution Log（策略建议与执行审计）
  - 增强规则引擎（队列生成、幂等与过期）
  - Dashboard 2.0（观察/决策/执行 + 安全写操作）

## Quick Start

### 1. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install sqlalchemy alembic pydantic-settings apscheduler requests yfinance python-dateutil psycopg2-binary pytest
```

### 2. Configure env
```bash
cp .env.example .env
# 修改 DATABASE_URL/FRED_API_KEY
# 生产环境建议额外配置:
# API_KEY=...
# DASHBOARD_WRITE_TOKEN=...
```

### 3. Apply migration
```bash
alembic upgrade head
```

### 4. CLI examples
```bash
python -m src.cli fetch market --source yfinance --symbol SPY --market US --start 2026-01-01 --end 2026-02-01 --incremental
python -m src.cli fetch fundamental --symbol 600000 --market CN --asof 2026-02-01 --incremental
python -m src.cli fetch macro --series CPIAUCSL --source fred --market US --start 2025-01-01 --end 2026-02-01 --incremental
python -m src.cli quality check --table raw_price --date 2026-02-01 --out /tmp/quality.json
python -m src.cli scheduler run-once
```

## Testing
```bash
pytest
```

## Docs
- [FRAMEWORK](docs/FRAMEWORK.md)
- [USAGE](docs/USAGE.md)
- [CHANGELOG](docs/CHANGELOG.md)
- [FAQ](docs/FAQ.md)
- [ERD](docs/ERD.md)
- [Phase 5 Update & Usage](docs/README_PHASE5.md)
