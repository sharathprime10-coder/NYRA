from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NYRA Backend"
    DATABASE_URL: str = "postgresql://nyra_user:nyra_password@localhost:5432/nyra_db"
    GEMINI_API_KEY: str = ""
    JWT_SECRET: str
    
    @property
    def jwt_secret_key(self) -> str:
        if self.JWT_SECRET == "supersecretjwtkey_replace_me_in_production":
            raise ValueError("CRITICAL SECURITY RISK: JWT_SECRET is using the default insecure value.")
        return self.JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GROQ_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    CEREBRAS_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
