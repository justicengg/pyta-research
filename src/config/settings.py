from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    database_url: str = 'sqlite:///./pyta.db'
    fred_api_key: str = ''
    scheduler_timezone: str = 'Asia/Shanghai'
    scheduler_cron_hour: int = 18
    scheduler_cron_minute: int = 0

    # Pipeline watchlists — override via .env with JSON arrays, e.g.:
    #   PIPELINE_CN_SYMBOLS=["sh.600000","sh.000001"]
    #   PIPELINE_US_SYMBOLS=["SPY","QQQ"]
    #   PIPELINE_CN_FUNDAMENTAL_SYMBOLS=["600000","000001"]
    #   PIPELINE_MACRO_SERIES=["CPIAUCSL:US:fred","UNRATE:US:fred"]
    pipeline_cn_symbols: list[str] = ['sh.600000']
    pipeline_us_symbols: list[str] = ['SPY']
    pipeline_cn_fundamental_symbols: list[str] = ['600000']
    pipeline_macro_series: list[str] = ['CPIAUCSL:US:fred']

    # Screener rules — format: "factor_name:operator:threshold"
    # Supported operators: >= <= > < ==
    # Rules are evaluated only when the factor exists for a symbol (missing → skipped).
    # A symbol becomes a candidate when ALL evaluated rules pass AND at least one rule matched.
    # Override via .env, e.g.:
    #   SCREENER_RULES=["roe_latest:>=:0.10","momentum_20d:>=:0.0"]
    screener_rules: list[str] = [
        'roe_latest:>=:0.08',
        'momentum_20d:>=:0.0',
        'debt_ratio_latest:<=:0.70',
        'volume_ratio_5_20:>=:0.80',
    ]

    # Strategy card stop-loss configuration (大呆子 CardGenerator)
    # method: 'pct' = fixed percentage below entry_price
    #         'atr' = entry_price - multiplier * ATR(window)
    # Rules are documented in FRAMEWORK.md; override via .env, e.g.:
    #   STRATEGY_STOP_LOSS_METHOD=atr
    #   STRATEGY_STOP_LOSS_PCT=0.10
    strategy_stop_loss_method: str = 'pct'
    strategy_stop_loss_pct: float = 0.08          # 8% fixed stop-loss
    strategy_stop_loss_atr_window: int = 14       # ATR period (trading days)
    strategy_stop_loss_atr_multiplier: float = 2.0  # stop = entry - multiplier * ATR


settings = Settings()
