# AgentX API Reference

This document provides detailed API documentation for all AgentX components.

## Base Agent

### `BaseAgent`

Base class for all agents in the system.

```python
class BaseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.memory_manager = self._setup_memory()
        self.metrics = self._setup_metrics()
        self.llm = self._setup_llm()

    async def initialize(self) -> None:
        """Initialize the agent"""
        pass

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data"""
        pass

    async def cleanup(self) -> None:
        """Clean up resources"""
        pass
```

### `AgentConfig`

Configuration class for agents.

```python
class AgentConfig(BaseModel):
    name: str
    host: str = "localhost"
    port: int
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    model_name: str = "gemini-pro"
    temperature: float = 0.7
    memory_path: str = "data/memory"
```

## Memory Manager

### `MemoryManager`

Manages different types of memory for agents.

```python
class MemoryManager:
    def __init__(self, config: Dict[str, Any]):
        self.vector_store = self._setup_vector_store()
        self.conversation_store = self._setup_conversation_store()

    async def add_interaction(
        self,
        interaction_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a new interaction to memory"""
        pass

    async def search_similar_interactions(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar past interactions"""
        pass

    async def get_recent_interactions(
        self,
        limit: int = 10,
        interaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent interactions"""
        pass

    async def get_conversation_context(
        self,
        limit: int = 5
    ) -> str:
        """Get recent conversation context"""
        pass
```

## Specialized Agents

### `SEOOptimizationAgent`

Agent for SEO optimization tasks.

```python
class SEOOptimizationAgent(BaseAgent):
    async def analyze_meta_tags(
        self,
        metadata: Dict[str, Any]
    ) -> List[SEOSuggestion]:
        """Analyze and suggest improvements for meta tags"""
        pass

    async def generate_seo_improvements(
        self,
        suggestions: List[SEOSuggestion]
    ) -> List[SEOSuggestion]:
        """Generate improved values for SEO suggestions"""
        pass

    async def analyze_content_structure(
        self,
        metadata: Dict[str, Any]
    ) -> List[SEOSuggestion]:
        """Analyze and suggest improvements for content structure"""
        pass
```

### `ContentUpdateAgent`

Agent for content update tasks.

```python
class ContentUpdateAgent(BaseAgent):
    async def analyze_content(
        self,
        content: Dict[str, Any]
    ) -> List[ContentUpdate]:
        """Analyze content for updates"""
        pass

    async def update_content(
        self,
        updates: List[ContentUpdate]
    ) -> List[ContentUpdate]:
        """Update content based on suggestions"""
        pass
```

### `ErrorFixingAgent`

Agent for error fixing tasks.

```python
class ErrorFixingAgent(BaseAgent):
    async def detect_errors(
        self,
        content: Dict[str, Any]
    ) -> List[Error]:
        """Detect errors in content"""
        pass

    async def fix_errors(
        self,
        errors: List[Error]
    ) -> List[Error]:
        """Fix detected errors"""
        pass
```

### `ContentGenerationAgent`

Agent for content generation tasks.

```python
class ContentGenerationAgent(BaseAgent):
    async def generate_content(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate new content"""
        pass

    async def refine_content(
        self,
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine existing content"""
        pass
```

### `PerformanceMonitoringAgent`

Agent for performance monitoring tasks.

```python
class PerformanceMonitoringAgent(BaseAgent):
    async def collect_metrics(
        self,
        url: str
    ) -> Dict[str, Any]:
        """Collect performance metrics"""
        pass

    async def analyze_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> List[PerformanceSuggestion]:
        """Analyze performance metrics"""
        pass
```

## System Configuration

### `SystemConfig`

System-wide configuration class.

```python
class SystemConfig(BaseModel):
    # Agent ports
    READ_AGENT_PORT: int = 8001
    MANAGER_AGENT_PORT: int = 8000
    CONTENT_UPDATE_AGENT_PORT: int = 8002
    SEO_OPTIMIZATION_AGENT_PORT: int = 8003
    ERROR_FIXING_AGENT_PORT: int = 8004
    CONTENT_GENERATION_AGENT_PORT: int = 8005
    PERFORMANCE_MONITORING_AGENT_PORT: int = 8006
    CICD_DEPLOYMENT_AGENT_PORT: int = 8007

    # Agent configurations
    agent_configs: Dict[str, AgentConfig]

    # Workflow settings
    workflow_settings: Dict[str, Any]

    # Memory configuration
    memory_config: Dict[str, Any]

    # Monitoring configuration
    monitoring_config: Dict[str, Any]
```

## Data Models

### `SEOSuggestion`

Model for SEO improvement suggestions.

```python
class SEOSuggestion(BaseModel):
    type: str  # meta, content, structure
    priority: int
    current_value: str
    suggested_value: str
    reason: str
```

### `ContentUpdate`

Model for content update suggestions.

```python
class ContentUpdate(BaseModel):
    section: str
    current_content: str
    suggested_content: str
    reason: str
    priority: int
```

### `Error`

Model for detected errors.

```python
class Error(BaseModel):
    type: str
    location: str
    description: str
    fix: str
    priority: int
```

### `PerformanceSuggestion`

Model for performance improvement suggestions.

```python
class PerformanceSuggestion(BaseModel):
    metric: str
    current_value: float
    target_value: float
    suggestion: str
    priority: int
```

## CLI Commands

### `agentx init`

Initialize AgentX configuration.

```python
@click.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--force', '-f', is_flag=True,
              help='Force overwrite of existing configuration file')
def init(config: str, force: bool):
    """Initialize AgentX configuration"""
    pass
```

### `agentx run`

Run the AgentX pipeline.

```python
@click.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without applying them')
def run(config: str, dry_run: bool):
    """Run the AgentX pipeline"""
    pass
```

### `agentx dev`

Run AgentX in development mode.

```python
@click.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--port', '-p', default=8000,
              help='Port for development server')
def dev(config: str, port: int):
    """Run AgentX in development mode"""
    pass
```

### `agentx build`

Build AgentX for production.

```python
@click.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--output', '-o', default='dist',
              help='Output directory for build artifacts')
def build(config: str, output: str):
    """Build AgentX for production"""
    pass
``` 