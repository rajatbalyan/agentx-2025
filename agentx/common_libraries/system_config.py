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
        
        return cls(**config_data) 