"""CLI commands for AgentX framework."""

import os
import click
import yaml
from typing import Optional
import uvicorn
from agentx.system import AgentXSystem

@click.group()
def cli():
    """AgentX CLI - Autonomous Website Maintenance Framework"""
    pass

@cli.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--force', '-f', is_flag=True,
              help='Force overwrite existing configuration')
def init(config: str, force: bool):
    """Initialize AgentX configuration."""
    if os.path.exists(config) and not force:
        click.echo(f"Configuration file {config} already exists. Use --force to overwrite.")
        return

    # Create default configuration
    default_config = {
        'website_url': 'https://your-website.com',
        'agents': {
            'content_update': True,
            'seo_optimization': True,
            'error_fixing': True,
            'content_generation': True,
            'performance_monitoring': True
        },
        'schedule': {
            'frequency': 'daily',
            'time': '00:00'
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/agentx.log',
            'max_size': '100MB',
            'backup_count': 5
        },
        'models': {
            'seo_agent': 'models/seo_agent/',
            'content_generation': 'models/content_gen/',
            'error_fixing': 'models/error_fix/'
        },
        'github': {
            'token': 'your-github-token',
            'repo': 'owner/repo',
            'branch': 'main'
        },
        'api_keys': {
            'google': 'your-google-api-key'
        }
    }

    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('models/seo_agent', exist_ok=True)
    os.makedirs('models/content_gen', exist_ok=True)
    os.makedirs('models/error_fix', exist_ok=True)
    os.makedirs('data/memory/vectors', exist_ok=True)
    os.makedirs('data/memory/conversations', exist_ok=True)

    # Write configuration file
    with open(config, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)

    click.echo(f"Created configuration file: {config}")
    click.echo("Please edit the configuration file with your settings.")

@cli.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--dry-run', is_flag=True,
              help='Preview changes without applying them')
def run(config: str, dry_run: bool):
    """Run the AgentX pipeline."""
    if not os.path.exists(config):
        click.echo(f"Configuration file {config} not found. Run 'agentx init' first.")
        return

    # Load configuration
    with open(config) as f:
        config_data = yaml.safe_load(f)

    # Initialize system
    system = AgentXSystem()
    
    if dry_run:
        click.echo("Dry run - previewing changes:")
        click.echo(yaml.dump(config_data, default_flow_style=False))
        return

    try:
        # Initialize and start the system
        system.initialize_agents()
        click.echo("AgentX system started successfully.")
        
        # Start the main application
        uvicorn.run(system.app, host="0.0.0.0", port=8000)
        
    except Exception as e:
        click.echo(f"Error starting AgentX: {str(e)}")

@cli.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--port', '-p', default=8000,
              help='Port for development server')
def dev(config: str, port: int):
    """Run AgentX in development mode."""
    if not os.path.exists(config):
        click.echo(f"Configuration file {config} not found. Run 'agentx init' first.")
        return

    # Set development environment
    os.environ['AGENTX_DEV'] = 'true'
    
    try:
        # Initialize system with development settings
        system = AgentXSystem()
        system.initialize_agents()
        
        click.echo("Starting AgentX in development mode...")
        click.echo(f"Development server running at http://localhost:{port}")
        
        # Start development server with auto-reload
        uvicorn.run(
            "agentx.system:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            reload_dirs=["agentx"]
        )
        
    except Exception as e:
        click.echo(f"Error starting development server: {str(e)}")

@cli.command()
@click.option('--config', '-c', default='agentx.config.yaml',
              help='Path to configuration file')
@click.option('--output', '-o', default='dist',
              help='Output directory for build artifacts')
def build(config: str, output: str):
    """Build AgentX for production."""
    if not os.path.exists(config):
        click.echo(f"Configuration file {config} not found. Run 'agentx init' first.")
        return

    try:
        # Create output directory
        os.makedirs(output, exist_ok=True)
        
        # Load configuration
        with open(config) as f:
            config_data = yaml.safe_load(f)
        
        # Validate configuration
        required_keys = ['website_url', 'agents', 'api_keys']
        missing_keys = [key for key in required_keys if key not in config_data]
        if missing_keys:
            click.echo(f"Missing required configuration keys: {', '.join(missing_keys)}")
            return
        
        # Copy necessary files to output directory
        import shutil
        shutil.copy2(config, os.path.join(output, 'agentx.config.yaml'))
        
        # Create directory structure
        os.makedirs(os.path.join(output, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(output, 'data'), exist_ok=True)
        os.makedirs(os.path.join(output, 'models'), exist_ok=True)
        
        click.echo(f"Build completed. Output directory: {output}")
        click.echo("You can now deploy the contents of the output directory.")
        
    except Exception as e:
        click.echo(f"Error building AgentX: {str(e)}")

if __name__ == '__main__':
    cli() 