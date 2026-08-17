from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    PROJECT_NAME: str = "Contact Book Agent Bot"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8004
    PLATFORM_API_URL: str = "https://dilushaplatform.mudraidtesting.online/api/v1"
    PLATFORM_API_KEY: str = ""
    ENVIRONMENT: str = "development"
    MONGODB_URL: str = ""

    # LLM Settings
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

settings = Settings()
