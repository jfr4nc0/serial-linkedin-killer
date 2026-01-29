"""Configuration management for the CLI client."""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, validator


class JobSearchConfig(BaseModel):
    """Configuration for a single job search."""

    job_title: str
    location: str
    monthly_salary: int
    limit: int = 20

    @validator("monthly_salary")
    def salary_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Monthly salary must be positive")
        return v

    @validator("limit")
    def limit_must_be_reasonable(cls, v):
        if v <= 0 or v > 100:
            raise ValueError("Job limit must be between 1 and 100")
        return v


class CLIConfig(BaseModel):
    """Main CLI configuration."""

    # LinkedIn credentials
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None

    # File paths
    cv_file_path: Optional[str] = None

    # MCP server configuration
    mcp_server_host: str = "localhost"
    mcp_server_port: int = 3000

    # Job searches
    job_searches: List[JobSearchConfig] = []

    # Output configuration
    output_format: str = "rich"  # "rich", "json", "simple"
    save_results: bool = True
    results_directory: str = "./results"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def load_from_file(cls, config_path: str) -> "CLIConfig":
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Convert job_searches to JobSearchConfig objects
        if "job_searches" in data:
            data["job_searches"] = [
                JobSearchConfig(**search) for search in data["job_searches"]
            ]

        return cls(**data)

    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        # Convert to dict and handle JobSearchConfig objects
        data = self.dict()
        if "job_searches" in data:
            data["job_searches"] = [
                search.dict() if hasattr(search, "dict") else search
                for search in data["job_searches"]
            ]

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    @classmethod
    def from_env(cls) -> "CLIConfig":
        """Create configuration from environment variables."""
        return cls(
            linkedin_email=os.getenv("LINKEDIN_EMAIL"),
            linkedin_password=os.getenv("LINKEDIN_PASSWORD"),
            cv_file_path=os.getenv("CV_FILE_PATH"),
            mcp_server_host=os.getenv("MCP_SERVER_HOST", "localhost"),
            mcp_server_port=int(os.getenv("MCP_SERVER_PORT", "3000")),
        )

    def merge_with_env(self) -> "CLIConfig":
        """Merge current config with environment variables (env takes precedence)."""
        env_config = self.from_env()

        # Update fields that are set in environment
        update_dict = {}
        if env_config.linkedin_email:
            update_dict["linkedin_email"] = env_config.linkedin_email
        if env_config.linkedin_password:
            update_dict["linkedin_password"] = env_config.linkedin_password
        if env_config.cv_file_path:
            update_dict["cv_file_path"] = env_config.cv_file_path

        update_dict["mcp_server_host"] = env_config.mcp_server_host
        update_dict["mcp_server_port"] = env_config.mcp_server_port

        return self.model_copy(update=update_dict)

    def validate_required_fields(self) -> List[str]:
        """Validate that required fields are present. Returns list of missing fields."""
        missing = []

        if not self.linkedin_email:
            missing.append("linkedin_email")
        if not self.linkedin_password:
            missing.append("linkedin_password")
        if not self.cv_file_path:
            missing.append("cv_file_path")
        elif not os.path.exists(self.cv_file_path):
            missing.append(f"cv_file_path (file not found: {self.cv_file_path})")

        return missing

    def get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # First check current directory
        current_dir_config = Path.cwd() / "config.yaml"
        if current_dir_config.exists():
            return str(current_dir_config)

        # Then check examples directory
        examples_config = Path.cwd() / "examples" / "config.yaml"
        if examples_config.exists():
            return str(examples_config)

        # Finally fall back to home directory
        home = Path.home()
        return str(home / ".job-applier" / "config.yaml")
