from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Contact Book Agent Bot"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8001
    PLATFORM_API_URL: str = "http://localhost:8000/api/v1"
    SECRET_KEY: str = "bot_testing_secret_key_12345"
    ENVIRONMENT: str = "development"

    # LLM Settings
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
