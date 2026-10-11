from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # AI Engine (Groq High-Speed Inference)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_VISION_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_TEXT_MODEL: str = "openai/gpt-oss-120b"

    # AWS Infrastructure (DynamoDB & S3)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    DYNAMODB_TABLE: str = "CivicPulseTable"
    S3_BUCKET: str = "civicpulse-evidence-store"

    # Portal Automation & Live Municipal Navigation
    PORTAL_MODE: str = "mock"  # "live" or "mock"
    DEFAULT_PORTAL_URL: str = "https://complaint.pmc.gov.in/"
    MOCK_PORTAL_URL: str = "http://localhost:8000/mock-pmc-portal"
    HEADLESS_BROWSER: bool = False

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()