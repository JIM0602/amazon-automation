"""Application settings."""

# pyright: reportAssignmentType=false, reportIncompatibleVariableOverride=false, reportDeprecated=false

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
    # Database
    DATABASE_URL: str = Field("sqlite:///./app.db", description="Database connection URL")  # pyright: ignore[reportAssignmentType]

    # 数据库配置
    DATABASE_URL: str = Field("sqlite:///./app.db", description="PostgreSQL连接字符串")  # pyright: ignore[reportAssignmentType]

    # OpenAI配置
    OPENAI_API_KEY: str = Field("", description="OpenAI API密钥")  # pyright: ignore[reportAssignmentType]
    OPENAI_MODEL: str = Field("gpt-4o-mini", description="默认使用的OpenAI模型")  # pyright: ignore[reportAssignmentType]

    # OpenRouter配置（可选）
    OPENROUTER_API_KEY: Optional[str] = Field(None, description="OpenRouter API密钥")

    # Anthropic配置（可选）
    ANTHROPIC_API_KEY: Optional[str] = Field(None, description="Anthropic API密钥")

    # 飞书配置
    FEISHU_APP_ID: str = Field("", description="飞书应用ID")  # pyright: ignore[reportAssignmentType]
    FEISHU_APP_SECRET: str = Field("", description="飞书应用密钥")  # pyright: ignore[reportAssignmentType]
    FEISHU_VERIFY_TOKEN: Optional[str] = Field(None, description="飞书回调验证Token")
    FEISHU_ENCRYPT_KEY: Optional[str] = Field(None, description="飞书回调加密Key")
    FEISHU_TEST_CHAT_ID: Optional[str] = Field(None, description="测试飞书群ID")

    # 卖家精灵配置
    SELLER_SPRITE_API_KEY: Optional[str] = Field(None, description="卖家精灵API密钥")
    SELLER_SPRITE_MCP_ENDPOINT: str = Field("https://mcp.sellersprite.com/mcp", description="卖家精灵MCP端点")  # pyright: ignore[reportAssignmentType]
    SELLER_SPRITE_USE_MOCK: bool = Field(True, description="是否使用Mock数据")  # pyright: ignore[reportAssignmentType]

    # Amazon Advertising API
    AMAZON_ADS_CLIENT_ID: Optional[str] = Field(None, description="Amazon Ads LWA Client ID")
    AMAZON_ADS_CLIENT_SECRET: Optional[str] = Field(None, description="Amazon Ads LWA Client Secret")
    AMAZON_ADS_REFRESH_TOKEN: Optional[str] = Field(None, description="Amazon Ads OAuth Refresh Token")
    AMAZON_ADS_PROFILE_ID: Optional[str] = Field(None, description="Amazon Ads Profile ID (数字)")
    AMAZON_ADS_REGION: str = Field("NA", description="Amazon Ads区域: NA/EU/FE")  # pyright: ignore[reportAssignmentType]

    # LLM费用控制
    MAX_DAILY_LLM_COST_USD: float = Field(50.0, description="每日LLM最大费用(美元)")  # pyright: ignore[reportAssignmentType]

    # 系统行为控制
    DRY_RUN: bool = Field(False, description="dry-run模式：只分析不执行写入")  # pyright: ignore[reportAssignmentType]

    # Google Trends (Optional)
    GOOGLE_TRENDS_ENABLED: bool = Field(False, description="是否启用Google Trends集成")  # pyright: ignore[reportAssignmentType]
    GOOGLE_TRENDS_API_KEY: Optional[str] = Field(None, description="SerpApi API密钥")

    # 服务配置
    APP_HOST: str = Field("0.0.0.0", description="服务监听地址")  # pyright: ignore[reportAssignmentType]
    APP_PORT: int = Field(8000, description="服务端口")  # pyright: ignore[reportAssignmentType]

    # 日志级别
    LOG_LEVEL: str = Field("INFO", description="日志级别")  # pyright: ignore[reportAssignmentType]

    # Amazon SP-API
    AMAZON_SP_API_CLIENT_ID: Optional[str] = Field(None, description="SP-API LWA Client ID")
    AMAZON_SP_API_CLIENT_SECRET: Optional[str] = Field(None, description="SP-API LWA Client Secret")
    AMAZON_SP_API_APP_ID: Optional[str] = Field(None, description="SP-API Application ID")
    AMAZON_SP_API_REFRESH_TOKEN: Optional[str] = Field(None, description="SP-API LWA Refresh Token")
    AMAZON_MARKETPLACE_ID: str = Field("ATVPDKIKX0DER", description="US marketplace ID")  # pyright: ignore[reportAssignmentType]

    class Config:
        env_file = ".env"  # pyright: ignore[reportAssignmentType]
        env_file_encoding = "utf-8"  # pyright: ignore[reportAssignmentType]
        case_sensitive = True  # pyright: ignore[reportAssignmentType]


settings = Settings()
