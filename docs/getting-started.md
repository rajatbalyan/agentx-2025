# Getting Started with AgentX

This guide will help you get started with AgentX, from installation to running your first website maintenance task.

## Installation

### Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- Git

### Using pip

```bash
pip install agentx
```

### From Source

```bash
git clone https://github.com/yourusername/agentx.git
cd agentx
pip install -e .
```

## Quick Start

1. Initialize AgentX configuration:
```bash
agentx init
```

2. Edit the generated `agentx.config.yaml` file with your settings:
```yaml
website_url: https://your-website.com
agents:
  content_update: true
  seo_optimization: true
  error_fixing: true
  content_generation: true
  performance_monitoring: true
schedule:
  frequency: daily
  time: "00:00"
logging:
  level: INFO
  file: logs/agentx.log
  max_size: 100MB
  backup_count: 5
models:
  seo_agent: models/seo_agent/
  content_generation: models/content_gen/
  error_fixing: models/error_fix/
github:
  token: your-github-token
  repo: owner/repo
  branch: main
api_keys:
  google: your-google-api-key
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run AgentX:
```bash
agentx run
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key_here
GITHUB_TOKEN=your_github_token_here

# Website Configuration
TARGET_WEBSITE=https://example.com
SCAN_INTERVAL=3600  # in seconds

# Agent Configuration
MANAGER_AGENT_PORT=8000
READ_AGENT_PORT=8001
CONTENT_UPDATE_AGENT_PORT=8002
SEO_OPTIMIZATION_AGENT_PORT=8003
ERROR_FIXING_AGENT_PORT=8004
CONTENT_GENERATION_AGENT_PORT=8005
PERFORMANCE_MONITORING_AGENT_PORT=8006
CICD_DEPLOYMENT_AGENT_PORT=8007

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/agentx.log

# Memory Configuration
MEMORY_PATH=data/memory
VECTOR_STORE_PATH=data/memory/vectors
CONVERSATION_STORE_PATH=data/memory/conversations

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin

# Model Paths
SEO_MODEL_PATH=models/seo_agent/
CONTENT_GEN_MODEL_PATH=models/content_gen/
ERROR_FIX_MODEL_PATH=models/error_fix/

# GitHub Configuration
GITHUB_REPO=owner/repo
GITHUB_BRANCH=main

# Development Mode
AGENTX_DEV=false
```

### Configuration File

The `agentx.config.yaml` file controls various aspects of the system:

1. **Website Configuration**
   - `website_url`: The URL to monitor
   - `schedule`: Maintenance frequency and time

2. **Agent Configuration**
   - Enable/disable specific agents
   - Configure agent-specific settings

3. **Logging Configuration**
   - Log level and file settings
   - Log rotation settings

4. **Model Configuration**
   - Paths to fine-tuned models
   - Model-specific settings

5. **GitHub Integration**
   - Repository settings
   - Branch configuration

## Development Mode

For development with hot-reloading and verbose logging:

```bash
agentx dev
```

## Building for Production

To build the system for production deployment:

```bash
agentx build
```

This will create a `dist` directory with all necessary files for deployment.

## Next Steps

1. Read the [Architecture Guide](architecture.md) to understand how AgentX works
2. Check the [API Reference](api-reference.md) for detailed documentation
3. Follow the [Development Guide](development.md) to contribute to the project
4. See the [Deployment Guide](deployment.md) for production deployment options 