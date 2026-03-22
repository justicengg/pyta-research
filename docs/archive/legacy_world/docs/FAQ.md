# 常见问题 (FAQ)

## 数据相关

**Q: baostock 登录报错 / 无法连接怎么办？**
baostock 需要网络访问 `www.baostock.com`。确认网络正常后重试，baostock 的 login/logout 已内置在 default adapter 中，会自动处理。

**Q: FRED API 返回空数据？**
检查 `.env` 中的 `FRED_API_KEY` 是否正确，可在 [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) 免费申请。

**Q: 数据库用 SQLite 还是 PostgreSQL？**
- 本地开发：默认 SQLite（`sqlite:///./pyta.db`），零配置
- 生产/并发：换 PostgreSQL，修改 `.env` 中的 `DATABASE_URL` 即可，代码无需改动

**Q: 重复拉取数据会不会写入重复行？**
不会。insert 层使用 SAVEPOINT + IntegrityError 捕获，遇到重复 key 自动跳过，并发安全。

**Q: 如何只拉取增量数据（不重复拉历史）？**
所有 fetch 命令加 `--incremental` 参数，会自动从上次最大日期的次日开始拉取。

**Q: 基本面的 publish_date 是怎么得到的？**
baostock `query_profit_data` 返回 `pubDate`（公告日）字段，直接使用。如果 API 未返回，fallback 为 `statDate + 30天`。Point-in-Time 过滤以 `publish_date` 为准，不会用到未来数据。

**Q: quality_status 字段有什么用？**
数据入库后初始为 `pending`，经过质量检查后可标记为 `passed` 或 `flagged`（当前质量检查只生成报告，不自动更新字段——后续 Phase 2 会完善）。

## 标的与配置相关

**Q: 如何添加新标的？**
修改 `.env` 中对应的列表字段，无需改代码，重启调度器生效。详见 [USAGE.md](./USAGE.md#扩展标的池)。

**Q: CN 行情 symbol 和基本面 symbol 格式不一样？**
baostock 行情接口使用带交易所前缀的格式（如 `sh.600000`），基本面接口使用纯代码（如 `600000`）。在 `.env` 中分别配置 `PIPELINE_CN_SYMBOLS` 和 `PIPELINE_CN_FUNDAMENTAL_SYMBOLS`。

**Q: 宏观序列格式是什么？**
`PIPELINE_MACRO_SERIES` 中每个条目格式为 `series:market:source`，例如 `CPIAUCSL:US:fred`。

## 工具链相关

**Q: 如何在 CI 中运行管道？**
使用 `python -m src.cli scheduler run-once`，配合 GitHub Actions 的 schedule trigger。参考 `.github/workflows/` 中的配置。

**Q: 调度器时区如何修改？**
在 `.env` 中设置 `SCHEDULER_TIMEZONE`（默认 `Asia/Shanghai`）和触发时间 `SCHEDULER_CRON_HOUR` / `SCHEDULER_CRON_MINUTE`。
