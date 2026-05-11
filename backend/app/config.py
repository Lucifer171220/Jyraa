from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_server: str = "mssql+pyodbc://@localhost\SQLEXPRESS02/JiraDB?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"

    # JWT
    secret_key: str = "your-secret-key-change-in-production-minimum-32-characters"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30 * 24 * 60  # 30 days

    # CORS
    frontend_url: str = "http://localhost:3000"

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"

    # SMTP / Gmail automation
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_sender_email: Optional[str] = None
    smtp_use_tls: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
