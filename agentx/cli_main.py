"""CLI main entry point for Sentry framework."""

import os
import click
import yaml
import shutil
import structlog
import asyncio
from pathlib import Path
from typing import Optional
import uvicorn
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress
from rich import print as rprint
from agentx.system import AgentXSystem

logger = structlog.get_logger()
console = Console()

# Default configuration template
CONFIG_TEMPLATE = """# Sentry Configuration Template
version: '1.0'

# Required System Configuration
website_url: "https://metacatalyst.in"  # URL of the website to monitor
scan_interval: 3600  # Scan interval in seconds (default: 1 hour)

# API Keys Configuration
api_keys:
  google_api_key: ""  # Set via environment variable GOOGLE_API_KEY
  github_token: ""    # Set via environment variable GITHUB_TOKEN

# GitHub Configuration
github:
  repo_owner: ""  # Set via environment variable GITHUB_OWNER
  repo_name: ""   # Set via environment variable GITHUB_REPO
  branch: "main"  # Set via environment variable GITHUB_BRANCH
  auto_merge: false
  labels:
    - agentx
    - automated

# Workspace Configuration
workspace:
  path: "."  # Will be overridden by WORKSPACE_PATH environment variable if set
  ignore_patterns:
    - "**/__pycache__/**"
    - "**/*.pyc"
    - "**/node_modules/**"
    - "**/.git/**"
    - "**/venv/**"
    - "**/env/**"

# Memory Configuration
memory:
  vector_store_path: "data/memory/vector_store"
  conversation_memory_path: "data/memory/conversations"

# Model Configuration
model:
  provider: "google"     # Model provider
  name: "gemini-pro"     # Model name
  model_path: "models"   # Path to store model files
  temperature: 0.7      # Model temperature
  max_tokens: 1000      # Maximum tokens per request
  top_p: 0.95          # Nucleus sampling parameter

# Logging Configuration
logging:
  level: "INFO"
  file: "logs/agentx.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Development Mode Configuration
development_mode:
  enabled: false
  debug: false
  auto_reload: false
  port: 8000

# Agent Configuration
agent_config:
  enabled_agents:
    - "content_update"
    - "seo_optimization"
    - "error_fixing"
    - "content_generation"
    - "performance_monitoring"
  max_retries: 3
  timeout: 300

# Schedule Configuration
schedule:
  frequency: "daily"           # Maintenance frequency (hourly, daily, weekly)
  time: "00:00"             # Time to run (UTC)
  max_concurrent: 3          # Maximum concurrent tasks
  retry:
    attempts: 3             # Number of retry attempts
    delay: 300             # Delay between retries (seconds)

# Agent Settings
agents:
  content_update: true         # Updates outdated content
  seo_optimization: true       # Optimizes meta tags and structure
  error_fixing: true          # Fixes detected errors
  content_generation: true     # Generates new content
  performance_monitoring: true # Monitors site performance

  settings:
    content_update:
      max_age_days: 30        # Maximum content age before update
      priority_paths:         # Paths to prioritize for updates
        - /blog
        - /news
        - /docs

    seo_optimization:
      min_score: 80          # Minimum SEO score to maintain
      focus_keywords: []      # List of focus keywords
      ignore_paths:          # Paths to ignore
        - /admin
        - /api

    error_fixing:
      severity_threshold: "warning"  # Minimum severity to fix
      auto_fix: true                # Automatically fix issues
      notify_on_fix: true           # Send notification on fix

    content_generation:
      max_length: 1000       # Maximum content length
      tone: "professional"   # Content tone
      languages:            # Supported languages
        - en
        - es

    performance_monitoring:
      metrics:              # Metrics to monitor
        - load_time
        - ttfb
        - fcp
      thresholds:          # Performance thresholds
        load_time: 3000    # ms
        ttfb: 600         # ms
        fcp: 1000         # ms"""

# Load environment variables from .env file
load_dotenv()

@click.group()
def cli():
    """Sentry CLI - Command line interface for website monitoring and optimization."""
    pass

@cli.command()
def init():
    """Initialize Sentry configuration with an interactive prompt."""
    try:
        console.print(Panel.fit("🚀 Welcome to Sentry Configuration", style="bold blue"))
        
        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        config_path = config_dir / "agentx.config.yaml"
        
        if config_path.exists():
            if not Confirm.ask("❓ Configuration file already exists. Overwrite?", default=False):
                return
        
        # Get user input with rich formatting
        console.print("\n[bold cyan]Essential Configuration[/bold cyan]")
        console.print("[dim]Please provide the following information:[/dim]")
        
        # Required parameters with validation
        website_url = Prompt.ask(
            "🌐 Website URL",
            default="https://example.com",
            show_default=True
        )
        
        google_api_key = Prompt.ask(
            "🔑 Google API Key",
            password=True,
            show_default=False
        )
        
        github_token = Prompt.ask(
            "🔑 GitHub Token",
            password=True,
            show_default=False
        )
        
        github_owner = Prompt.ask(
            "👤 GitHub Repository Owner",
            show_default=False
        )
        
        github_repo = Prompt.ask(
            "📁 GitHub Repository Name",
            show_default=False
        )
        
        workspace = Prompt.ask(
            "💼 Workspace Path",
            default=str(Path.cwd()),
            show_default=True
        )
        
        # Show progress for file operations
        with Progress() as progress:
            task1 = progress.add_task("[cyan]Setting up configuration...", total=3)
            
            # Load template from string and update configuration
            config_data = yaml.safe_load(CONFIG_TEMPLATE)
            progress.update(task1, advance=1)
            
            # Update configuration with user input
            config_data['website_url'] = website_url
            config_data['api_keys']['google_api_key'] = google_api_key
            config_data['api_keys']['github_token'] = github_token
            config_data['github']['repo_owner'] = github_owner
            config_data['github']['repo_name'] = github_repo
            config_data['workspace']['path'] = workspace
            
            # Write configuration
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            progress.update(task1, advance=1)
            
            # Create necessary directories
            dirs = [
                "logs",
                "data/memory/vectors",
                "data/memory/conversations",
                "temp",
                "models"
            ]
            
            for dir_path in dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            
            # Create .env file
            env_content = f"""GOOGLE_API_KEY={google_api_key}
GITHUB_TOKEN={github_token}
GITHUB_OWNER={github_owner}
GITHUB_REPO={github_repo}
WORKSPACE_PATH={workspace}
"""
            with open(".env", "w") as f:
                f.write(env_content)
            progress.update(task1, advance=1)
        
        # Success message
        console.print("\n[bold green]✨ Configuration completed successfully![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Configuration saved in [cyan]config/agentx.config.yaml[/cyan]")
        console.print("2. Environment variables saved in [cyan].env[/cyan]")
        console.print("3. Run [cyan]sentry dev[/cyan] to start development server")
        
    except Exception as e:
        logger.error("init_error", error=str(e))
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them")
def run(dry_run: bool):
    """Run the Sentry pipeline."""
    try:
        # Load configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            console.print("[bold red]Configuration file not found.[/bold red] Run 'sentry init' first.", err=True)
            return
        
        # Initialize system
        console.print("🚀 Initializing Sentry system...")
        system = AgentXSystem(str(config_path))
        
        async def run_pipeline():
            try:
                await system.initialize()
                console.print("✅ System initialized successfully")
                
                # Rest of the pipeline code remains the same as in commands.py
                # ... existing pipeline code ...
                
            except Exception as e:
                logger.error("pipeline_error", error=str(e))
                console.print(f"[bold red]Pipeline execution failed:[/bold red] {str(e)}")
                raise
            finally:
                await system.cleanup()
                console.print("🧹 System cleanup completed")
        
        asyncio.run(run_pipeline())
            
    except Exception as e:
        logger.error("run_error", error=str(e))
        console.print(f"[bold red]Error running pipeline:[/bold red] {str(e)}")

@cli.command()
def dev():
    """Run Sentry in development mode."""
    try:
        # Ensure environment variables are loaded
        load_dotenv()
        
        # Load configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            console.print("[bold red]Configuration file not found.[/bold red] Run 'sentry init' first.", err=True)
            return
        
        # Initialize system
        system = AgentXSystem(str(config_path))
        asyncio.run(system.initialize())
        
        console.print("🚀 Starting development server...")
        uvicorn.run(
            "agentx.api:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["agentx"],
            log_level="info"
        )
        
    except Exception as e:
        logger.error("dev_error", error=str(e))
        console.print(f"[bold red]Error starting development server:[/bold red] {str(e)}")

@cli.command()
@click.option("--output", "-o", default="dist", help="Output directory for built files")
def build(output: str):
    """Build Sentry for production."""
    try:
        # Validate configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            console.print("[bold red]Configuration file not found.[/bold red] Run 'sentry init' first.", err=True)
            return
        
        # Create output directory
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy necessary files
        files_to_copy = [
            "config/agentx.config.yaml",
            "agentx",
            "requirements.txt",
            "README.md"
        ]
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Building project...", total=len(files_to_copy))
            
            for file_path in files_to_copy:
                src = Path(file_path)
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, output_dir / src.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, output_dir / src.name)
                    console.print(f"✅ Copied: {file_path}")
                else:
                    console.print(f"⚠️  Warning: {file_path} not found", style="yellow")
                progress.update(task, advance=1)
        
        console.print(f"\n[bold green]✨ Build complete![/bold green] Output directory: {output_dir}")
        
    except Exception as e:
        logger.error("build_error", error=str(e))
        console.print(f"[bold red]Error building project:[/bold red] {str(e)}")

if __name__ == '__main__':
    cli()
