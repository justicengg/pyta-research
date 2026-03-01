from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    database_url: str = 'sqlite:///./pyta.db'
    fred_api_key: str = ''
    scheduler_timezone: str = 'Asia/Shanghai'
    scheduler_cron_hour: int = 18
    scheduler_cron_minute: int = 0


settings = Settings()
