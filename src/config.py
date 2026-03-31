from typing import Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - 本地最小回退，便于无依赖环境验证
    def Field(default=None, description: str | None = None):
        return default

    class BaseSettings:
        def __init_subclass__(cls, **kwargs):
            return super().__init_subclass__(**kwargs)

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True


class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = Field(..., description="PostgreSQL连接字符串")

    # OpenAI配置
    OPENAI_API_KEY: str = Field(..., description="OpenAI API密钥")
    OPENAI_MODEL: str = Field("gpt-4o-mini", description="默认使用的OpenAI模型")

    # Anthropic配置（可选）
    ANTHROPIC_API_KEY: Optional[str] = Field(None, description="Anthropic API密钥")

    # 飞书配置
    FEISHU_APP_ID: str = Field(..., description="飞书应用ID")
    FEISHU_APP_SECRET: str = Field(..., description="飞书应用密钥")
    FEISHU_VERIFY_TOKEN: Optional[str] = Field(None, description="飞书回调验证Token")
    FEISHU_ENCRYPT_KEY: Optional[str] = Field(None, description="飞书回调加密Key")
    FEISHU_TEST_CHAT_ID: Optional[str] = Field(None, description="测试飞书群ID")

    # 卖家精灵配置
    SELLER_SPRITE_API_KEY: Optional[str] = Field(None, description="卖家精灵API密钥")
    SELLER_SPRITE_USE_MOCK: bool = Field(True, description="是否使用Mock数据")

    # LLM费用控制
    MAX_DAILY_LLM_COST_USD: float = Field(50.0, description="每日LLM最大费用(美元)")

    # 系统行为控制
    DRY_RUN: bool = Field(False, description="dry-run模式：只分析不执行写入")

    # 服务配置
    APP_HOST: str = Field("0.0.0.0", description="服务监听地址")
    APP_PORT: int = Field(8000, description="服务端口")

    # 日志级别
    LOG_LEVEL: str = Field("INFO", description="日志级别")

    # Amazon SP-API（Phase 2）
    AMAZON_SP_API_ACCESS_KEY: Optional[str] = Field(None, description="SP-API Access Key")
    AMAZON_SP_API_SECRET_KEY: Optional[str] = Field(None, description="SP-API Secret Key")
    AMAZON_SP_API_REFRESH_TOKEN: Optional[str] = Field(None, description="SP-API Refresh Token")
    AMAZON_MARKETPLACE_ID: str = Field("ATVPDKIKX0DER", description="US marketplace ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
