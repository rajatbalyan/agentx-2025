"""Single source of truth for all Site-Sentry configuration."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional, Literal
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: Literal["nvidia_nim", "google", "groq", "openai"] = "nvidia_nim"
    # Model names per role
    manager_model: str = "deepseek-ai/deepseek-v3-2"
    agent_model: str = "deepseek-ai/deepseek-v4-flash"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    # Base URL — defaults to NVIDIA NIM
    base_url: str = "https://integrate.api.nvidia.com/v1"


class MemoryConfig(BaseModel):
    """ChromaDB vector memory configuration."""
    vector_store_path: str = "data/memory/vectors"
    collection_prefix: str = "sentry"
    enabled: bool = True


class GitHubConfig(BaseModel):
    """GitHub integration configuration."""
    repo_owner: str = ""
    repo_name: str = ""
    base_branch: str = "main"
    auto_merge: bool = False
    pr_labels: List[str] = ["site-sentry", "automated"]
    branch_prefix: str = "sentry/fix"


class AgentToggleConfig(BaseModel):
    """Which agents are active for this run."""
    seo: bool = True
    performance: bool = True
    error_fixing: bool = True
    content_update: bool = False   # off by default — more aggressive
    content_generation: bool = False  # off by default


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    file: Optional[str] = "logs/sentry.log"
    format: Literal["json", "text"] = "text"


class SentryConfig(BaseModel):
    """Root configuration model — single source of truth."""
    # Required
    website_url: str
    workspace_path: str = "."

    # Optional with defaults
    scan_interval: int = Field(default=3600, description="Seconds between scans")
    llm: LLMConfig = LLMConfig()
    memory: MemoryConfig = MemoryConfig()
    github: GitHubConfig = GitHubConfig()
    agents: AgentToggleConfig = AgentToggleConfig()
    logging: LoggingConfig = LoggingConfig()

    # API keys — always loaded from env, never from YAML
    _api_key: str = ""
    _github_token: str = ""

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("website_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("workspace_path")
    @classmethod
    def resolve_workspace(cls, v: str) -> str:
        return str(Path(v).resolve())

    @model_validator(mode="after")
    def load_secrets_from_env(self) -> "SentryConfig":
        """Always pull secrets from environment, never from YAML."""
        self._api_key = os.environ.get("NVIDIA_API_KEY", "")
        self._github_token = os.environ.get("GITHUB_TOKEN", "")
        return self

    @property
    def api_key(self) -> str:
        return os.environ.get("NVIDIA_API_KEY", "")

    @property
    def github_token(self) -> str:
        return os.environ.get("GITHUB_TOKEN", "")

    @classmethod
    def load(cls, config_path: str) -> "SentryConfig":
        """Load config from YAML file with env var overrides."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config not found at {config_path}. Run 'sentry init' first."
            )
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Allow env vars to override YAML top-level keys
        if os.environ.get("TARGET_URL"):
            data["website_url"] = os.environ["TARGET_URL"]
        if os.environ.get("WORKSPACE_PATH"):
            data["workspace_path"] = os.environ["WORKSPACE_PATH"]

        return cls(**data)

    @classmethod
    def default_config_path(cls) -> Path:
        return Path("sentry.config.yaml")
