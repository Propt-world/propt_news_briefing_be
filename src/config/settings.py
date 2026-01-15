import os
from typing import Optional
from pydantic_settings import BaseSettings
from langchain_openai import ChatOpenAI
from opik.integrations.langchain import OpikTracer
import opik
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # --- API Settings ---
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "News Article Extractor"

    # --- Server Settings ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # --- Redis Configuration ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_QUEUE_NAME: str = os.getenv("REDIS_QUEUE_NAME", "newsagent_jobs")
    REDIS_DLQ_NAME: str = os.getenv("REDIS_DLQ_NAME", "newsagent_dlq")

    # --- MongoDB Settings ---
    DATABASE_URL: str = os.getenv('DATABASE_URL', "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv('MONGO_DB_NAME', "newsagent")

    # Automatic SSL/TLS Handling for AWS DocumentDB
    def __init__(self, **data):
        super().__init__(**data)
        cert_path = "/app/certs/global-bundle.pem"
        if os.path.exists(cert_path) and "localhost" not in self.DATABASE_URL:
            if "tls=true" not in self.DATABASE_URL:
                separator = "&" if "?" in self.DATABASE_URL else "?"
                self.DATABASE_URL += f"{separator}tls=true&tlsCAFile={cert_path}&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"

    # --- AWS S3 Settings ---
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME: Optional[str] = os.getenv('S3_BUCKET_NAME')

    # --- AI Keys and URLs ---
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY')
    OPENAI_URL: str = os.getenv('OPENAI_URL')
    
    # --- Observability ---
    OPIK_API_KEY: str = os.getenv('OPIK_API_KEY')
    OPIK_WORKSPACE: str = os.getenv('OPIK_WORKSPACE')
    OPIK_PROJECT_NAME: str = os.getenv('OPIK_PROJECT_NAME')

    # --- Model Configuration ---
    MODEL_NAME: str = os.getenv('MODEL_NAME', 'gpt-4o-mini')
    MODEL_TEMPERATURE: float = float(os.getenv('MODEL_TEMPERATURE', 0.5))

    # --- Email / SMTP Configuration ---
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # --- Security ---
    WEBHOOK_URL: Optional[str] = os.getenv('WEBHOOK_URL')
    WEBHOOK_SECRET: Optional[str] = os.getenv('WEBHOOK_SECRET')

    # --- Scheduler Configuration ---
    MAIN_API_URL: str = os.getenv('MAIN_API_URL', 'http://localhost:8000')
    SUBMISSION_SOURCE_ID: str = os.getenv('SUBMISSION_SOURCE_ID', 'newsagent_scheduled_source')
    SCHEDULER_URL: str = os.getenv('SCHEDULER_URL', 'http://scheduler:8001')

    # =========================================================
    # NEW: NewsCast Service Settings (Audio Briefing)
    # =========================================================
    
    # 1. External Articles Service
    ARTICLES_SERVICE_URL: str = os.getenv("ARTICLES_SERVICE_URL", "http://articles-service:8080")
    ARTICLES_SERVICE_API_KEY: Optional[str] = os.getenv("ARTICLES_SERVICE_API_KEY")

    # 2. Text-to-Speech (TTS) Configuration
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "openai") 
    
    # Strictly using the requested model
    TTS_MODEL: str = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
    
    # Default Voice ID (fallback if not in user config)
    TTS_DEFAULT_VOICE: str = os.getenv("TTS_DEFAULT_VOICE", "alloy") 
    
    # Optional dedicated key if different from the main OPENAI_API_KEY
    TTS_API_KEY: Optional[str] = os.getenv("TTS_API_KEY")

    # =========================================================

    def get_opik_client(self, graph=None):
        if not self.OPIK_API_KEY:
            return None
        if not self.OPIK_WORKSPACE:
            return None

        opik.configure(
            api_key=self.OPIK_API_KEY,
            workspace=self.OPIK_WORKSPACE,
        )

        if graph:
            opik_tracer = OpikTracer(graph=graph, project_name=self.OPIK_PROJECT_NAME)
        else:
            opik_tracer = OpikTracer(project_name=self.OPIK_PROJECT_NAME)

        return opik_tracer

    def get_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.MODEL_NAME,
            temperature=self.MODEL_TEMPERATURE,
            openai_api_key=self.OPENAI_API_KEY
        )

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = 'utf-8'
        extra = "ignore"

settings = Settings()