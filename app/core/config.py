from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Survey System API"
    DEBUG: bool = False
    
    # 1. 数据库配置
    MONGO_INITDB_ROOT_USERNAME: str = "admin_user"
    MONGO_INITDB_ROOT_PASSWORD: str = "admin_secure_password"
    MONGO_DB_NAME: str = "survey_db"
    
    # MongoDB 连接字符串 (供 Python 后端 FastAPI 使用)
    MONGODB_URL: str = "mongodb://admin_user:admin_secure_password@localhost:27017/survey_db?authSource=admin"

    # 2. 身份认证模块配置 (JWT 密钥)
    SECRET_KEY: str = "your_super_secret_jwt_key_here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # Configuration for loading from .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
