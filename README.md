# AgentX - Autonomous Website Maintenance Framework

AgentX is a powerful framework for autonomous website maintenance, featuring a multi-agent architecture that handles content updates, SEO optimization, error fixing, and more.

## Features

- Multi-agent architecture with specialized agents for different tasks
- Persistent memory using LangMem and ChromaDB
- Integration with Google's Gemini API
- Automated CI/CD pipeline with GitHub integration
- Real-time monitoring and metrics with Prometheus and Grafana
- Docker support for easy deployment

## Installation

### Using pip

```bash
pip install agentx
```

### From source

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

3. Run AgentX:
```bash
agentx run
```

## Development

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

## Docker Deployment

1. Build the Docker image:
```bash
docker-compose build
```

2. Start the services:
```bash
docker-compose up -d
```

## CLI Commands

### `agentx init`

Initialize AgentX configuration:
```bash
agentx init [--config CONFIG_FILE] [--force]
```

Options:
- `--config, -c`: Path to configuration file (default: agentx.config.yaml)
- `--force, -f`: Force overwrite of existing configuration file

### `agentx run`

Run the AgentX pipeline:
```bash
agentx run [--config CONFIG_FILE] [--dry-run]
```

Options:
- `--config, -c`: Path to configuration file (default: agentx.config.yaml)
- `--dry-run`: Preview changes without applying them

### `agentx dev`

Run AgentX in development mode:
```bash
agentx dev [--config CONFIG_FILE] [--port PORT]
```

Options:
- `--config, -c`: Path to configuration file (default: agentx.config.yaml)
- `--port, -p`: Port for development server (default: 8000)

### `agentx build`

Build AgentX for production:
```bash
agentx build [--config CONFIG_FILE] [--output OUTPUT_DIR]
```

Options:
- `--config, -c`: Path to configuration file (default: agentx.config.yaml)
- `--output, -o`: Output directory for build artifacts (default: dist)

## Architecture

### Agents

1. **READ Agent**
   - Fetches and normalizes website data
   - Uses Playwright for dynamic content loading
   - Integrates with HTMLHint, WebHint, and Lighthouse

2. **Manager Agent**
   - Orchestrates workflow using LangGraph
   - Coordinates between specialized agents
   - Handles task delegation and error recovery

3. **Specialized Agents**
   - Content Update Agent: Updates outdated content
   - Error Fixing Agent: Detects and fixes issues
   - SEO Optimization Agent: Enhances metadata and structure
   - Content Generation Agent: Creates new content
   - Performance Monitoring Agent: Tracks metrics

4. **CI/CD Deployment Agent**
   - Manages GitHub integration
   - Handles branch creation and merging
   - Runs automated tests

### Memory Management

- Uses LangMem for persistent memory
- ChromaDB for vector storage
- Maintains conversation and document memory
- Supports context retrieval and similar interaction searching

### Monitoring

- Prometheus for metrics collection
- Grafana for visualization
- Real-time performance monitoring
- Error tracking and reporting

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 