"""Central configuration loader for agent.yaml with env var overrides."""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel


class LLMConfig(BaseModel):
    base_url: str = "http://localhost:8088/v1"
    api_key: str = "not-needed"
    temperature: float = 0.1
    max_tokens: int = 2000


class MCPServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 8000


class LinkedInConfig(BaseModel):
    email: str = ""
    password: str = ""


class BrowserConfig(BaseModel):
    headless: bool = False
    use_undetected: bool = True
    browser_type: str = "chrome"
    chrome_version: Optional[int] = None  # Force specific ChromeDriver version
    chrome_binary_path: Optional[str] = None  # Path to Chrome binary


class OutreachFilters(BaseModel):
    industry: List[str] = []
    country: List[str] = []
    size: List[str] = []


class OutreachConfig(BaseModel):
    dataset_path: str = "./data/free_company_dataset.csv"
    db_path: str = "./data/companies.db"
    message_template_path: str = ""
    message_template: str = ""
    employees_per_company: int = 10
    daily_message_limit: int = 50
    delay_between_messages_min: float = 30.0
    delay_between_messages_max: float = 120.0
    filters: OutreachFilters = OutreachFilters()


class CVConfig(BaseModel):
    file_path: str = "./data/cv_data.json"


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "localhost:9092"


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class DBConfig(BaseModel):
    url: str = "sqlite:///./data/agent.db"
    company_url: str = "sqlite:///./data/companies.db"


class ObservabilityConfig(BaseModel):
    langfuse_enabled: bool = False
    log_level: str = "INFO"


class AgentConfig(BaseModel):
    llm: LLMConfig = LLMConfig()
    mcp_server: MCPServerConfig = MCPServerConfig()
    linkedin: LinkedInConfig = LinkedInConfig()
    browser: BrowserConfig = BrowserConfig()
    outreach: OutreachConfig = OutreachConfig()
    cv: CVConfig = CVConfig()
    kafka: KafkaConfig = KafkaConfig()
    api: APIConfig = APIConfig()
    db: DBConfig = DBConfig()
    observability: ObservabilityConfig = ObservabilityConfig()


_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "agent.yaml"
_cached_config: Optional["AgentConfig"] = None


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """Load config from YAML file and merge with environment variable overrides.

    Priority: env vars > YAML file > defaults.
    """
    global _cached_config

    if _cached_config is not None and config_path is None:
        return _cached_config

    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH

    data: Dict = {}
    if path.exists():
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

    config = AgentConfig(**data)

    # Env var overrides
    env_overrides = {
        "linkedin.email": os.getenv("LINKEDIN_EMAIL"),
        "linkedin.password": os.getenv("LINKEDIN_PASSWORD"),
        "cv.file_path": os.getenv("CV_FILE_PATH"),
        "mcp_server.host": os.getenv("MCP_SERVER_HOST"),
        "mcp_server.port": os.getenv("MCP_SERVER_PORT"),
        "llm.base_url": os.getenv("LOCAL_LLM_BASE_URL"),
        "llm.api_key": os.getenv("LOCAL_LLM_API_KEY"),
        "kafka.bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        "api.host": os.getenv("API_HOST"),
        "api.port": os.getenv("API_PORT"),
        "db.url": os.getenv("DATABASE_URL"),
        "db.company_url": os.getenv("COMPANY_DATABASE_URL"),
        "observability.log_level": os.getenv("LOG_LEVEL"),
    }

    for dotted_key, value in env_overrides.items():
        if value is not None:
            parts = dotted_key.split(".")
            obj = config
            for part in parts[:-1]:
                obj = getattr(obj, part)
            field = parts[-1]
            field_info = type(obj).model_fields[field]
            cast_value = (
                field_info.annotation(value)
                if field_info.annotation in (int, float, bool)
                else value
            )
            setattr(obj, field, cast_value)

    if config_path is None:
        _cached_config = config

    return config
