"""System configuration for AgentX framework."""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel

class WorkspaceConfig(BaseModel):
    """Workspace configuration."""
    path: str = "."
    ignore_patterns: List[str] = [
        "**/__pycache__/**",
        "**/*.pyc",
        "**/node_modules/**",
        "**/.git/**",
        "**/venv/**",
        "**/env/**"
    ]

class MemoryConfig(BaseModel):
    """Memory configuration."""
    vector_store_path: str = "data/memory/vector_store"
    conversation_memory_path: str = "data/memory/conversations"

class ModelConfig(BaseModel):
    """Model configuration."""
    provider: str = "google"     # Model provider
    name: str = "gemini-pro"     # Model name
    model_path: str = "models"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.95         # Nucleus sampling parameter

class AgentConfig(BaseModel):
    """Agent configuration."""
    enabled_agents: List[str] = ["content_update", "seo_optimization", "error_fixing", "content_generation", "performance_monitoring"]
    max_retries: int = 3
    timeout: int = 300

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/agentx.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class DevelopmentConfig(BaseModel):
    """Development mode configuration."""
    enabled: bool = False
    debug: bool = False
    auto_reload: bool = False
    port: int = 8000

class GitHubConfig(BaseModel):
    """GitHub configuration."""
    repo_owner: str = ""
    repo_name: str = ""
    branch: str = "main"
    auto_merge: bool = False
    labels: List[str] = ["agentx", "automated"]

class SystemConfig(BaseModel):
    """Main system configuration."""
    website_url: str
    scan_interval: int = 300
    workspace: WorkspaceConfig = WorkspaceConfig()
    agent_config: AgentConfig = AgentConfig()
    memory: MemoryConfig = MemoryConfig()
    model: ModelConfig = ModelConfig()
    logging: LoggingConfig = LoggingConfig()
    development_mode: DevelopmentConfig = DevelopmentConfig()
    api_keys: Dict[str, str] = {}
    github: GitHubConfig = GitHubConfig()

    @classmethod
    def load(cls, config_path: str) -> 'SystemConfig':
        """Load configuration from file and environment variables."""
        import yaml
        
        # Load YAML config
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Override with environment variables
        config_data['api_keys'] = {
            'google_api_key': os.getenv('GOOGLE_API_KEY', config_data.get('api_keys', {}).get('google_api_key', '')),
            'github_token': os.getenv('GITHUB_TOKEN', config_data.get('api_keys', {}).get('github_token', ''))
        }

        # Handle GitHub configuration from environment variables
        if 'github' not in config_data:
            config_data['github'] = {}
        
        config_data['github'].update({
            'repo_owner': os.getenv('GITHUB_OWNER', config_data['github'].get('repo_owner', '')),
            'repo_name': os.getenv('GITHUB_REPO', config_data['github'].get('repo_name', '')),
            'branch': os.getenv('GITHUB_BRANCH', config_data['github'].get('branch', 'main'))
        })

        # Handle workspace path environment variable
        if isinstance(config_data.get('workspace'), dict):
            workspace_path = os.getenv('WORKSPACE_PATH', config_data['workspace'].get('path', '.'))
            config_data['workspace']['path'] = workspace_path
        
        return cls(**config_data)

    def validate_workspace(self) -> None:
        """Validate workspace configuration."""
        if not self.workspace.path or self.workspace.path.strip() == "":
            raise ValueError("No workspace path provided")
        
        # Expand environment variables and user home
        self.workspace.path = os.path.expandvars(os.path.expanduser(self.workspace.path))
        
        # Convert to absolute path if relative
        if not os.path.isabs(self.workspace.path):
            self.workspace.path = os.path.abspath(self.workspace.path)
        
        # Ensure directory exists
        if not os.path.exists(self.workspace.path):
            os.makedirs(self.workspace.path, exist_ok=True) 