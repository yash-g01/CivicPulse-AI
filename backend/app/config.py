from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # AI Engine (Gemini 2.5 Flash for Multimodal Vision)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # AWS Infrastructure (DynamoDB & S3)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    DYNAMODB_TABLE: str = "CivicPulseTable"
    S3_BUCKET: str = "civicpulse-evidence-store"

    # Portal Automation & Mock Fallback
    PORTAL_MODE: str = "live"  # "live" or "mock"
    DEFAULT_PORTAL_URL: str = "https://complaint.pmc.gov.in/"
    MOCK_PORTAL_URL: str = "http://localhost:8000/mock-pmc-portal"

    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()