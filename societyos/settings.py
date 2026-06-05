from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    qwen_api_key: str = Field(default="", alias="QWEN_API_KEY")
    qwen_base_url: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_BASE_URL",
    )
    qwen_model: str = Field(default="qwen-plus", alias="QWEN_MODEL")
    db_path: str = Field(default="./societyos.db", alias="SOCIETYOS_DB_PATH")
    reports_dir: str = Field(default="./reports", alias="SOCIETYOS_REPORTS_DIR")
    log_level: str = Field(default="INFO", alias="SOCIETYOS_LOG_LEVEL")


settings = Settings()
