from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    telegram_bot_token: str | None = None

    host: str = "0.0.0.0"
    port: int = 8000
    database_path: str = "data/tickets.db"
    knowledge_dir: str = "knowledge/faq"

    business_tz: str = "Europe/Kyiv"
    business_start_hour: int = 9
    business_end_hour: int = 18

    billing_wallet_address: str = "0xGATUM_DEMO_WALLET_ADDRESS"
    support_lead_webhook_url: str | None = None
    after_hours_check_enabled: bool = True

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def faq_path(self) -> Path:
        return Path(self.knowledge_dir)


settings = Settings()
