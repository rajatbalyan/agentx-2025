"""CLI commands for AgentX framework."""

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
from agentx.system import AgentXSystem

logger = structlog.get_logger()

# Load environment variables from .env file
load_dotenv()

@click.group()
def cli():
    """AgentX CLI - Command line interface for AgentX framework."""
    pass

@cli.command()
@click.option('--workspace', default=None, help='Path to the workspace directory')
def init(workspace: Optional[str]):
    """Initialize AgentX configuration."""
    try:
        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Copy template to config directory
        template_path = Path(__file__).parent.parent / "config" / "agentx.config.yaml.template"
        config_path = config_dir / "agentx.config.yaml"
        
        if config_path.exists():
            if not click.confirm("Configuration file already exists. Overwrite?"):
                return
        
        # Instead of loading and dumping YAML, directly copy the template
        # and then update only the workspace path
        shutil.copy2(template_path, config_path)
        
        # Update workspace path if provided
        if workspace:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            config_data['workspace']['path'] = workspace
            
            # Write back with sort_keys=False to preserve order
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
        click.echo(f"Created configuration file at {config_path}")
        
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
            click.echo(f"Created directory: {dir_path}")
            
        click.echo("\nNext steps:")
        click.echo("1. Set up your environment variables in .env:")
        click.echo("   GOOGLE_API_KEY=your-google-api-key")
        click.echo("   GITHUB_TOKEN=your-github-token")
        click.echo("2. Edit config/agentx.config.yaml if needed")
        click.echo("3. Run 'python -m agentx.cli dev' to start development server")
        
    except Exception as e:
        logger.error("init_error", error=str(e))
        click.echo(f"Error initializing configuration: {str(e)}", err=True)

@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them")
def run(dry_run: bool):
    """Run the AgentX pipeline."""
    try:
        # Load configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            click.echo("Configuration file not found. Run 'python -m agentx.cli init' first.", err=True)
            return
        
        # Initialize system
        click.echo("Initializing AgentX system...")
        system = AgentXSystem(str(config_path))
        
        async def run_pipeline():
            """Run the complete AgentX pipeline."""
            try:
                # Initialize the system
                await system.initialize()
                click.echo("✅ System initialized successfully")

                # Define the pipeline tasks
                pipeline_tasks = [
                    {
                        "task_type": "read",
                        "data": {
                            "url": system.config.website_url,
                            "scan_type": "full",
                            "description": "Initial website scan"
                        }
                    },
                    {
                        "task_type": "performance_monitoring",
                        "data": {
                            "type": "performance_audit",
                            "target": system.config.website_url
                        }
                    },
                    {
                        "task_type": "seo_optimization",
                        "data": {
                            "type": "seo_audit",
                            "target": system.config.website_url
                        }
                    },
                    {
                        "task_type": "content_generation",
                        "data": {
                            "type": "content_audit",
                            "target": system.config.website_url
                        }
                    },
                    {
                        "task_type": "error_fixing",
                        "data": {
                            "type": "error_audit",
                            "target": system.config.website_url
                        }
                    }
                ]

                if dry_run:
                    click.echo("\n🔍 Dry run mode - previewing changes...")
                    for task in pipeline_tasks:
                        click.echo(f"\nWould process task: {task['task_type']}")
                        click.echo(f"With data: {task['data']}")
                    click.echo("\n✨ Dry run completed - no changes were made")
                    return

                # Execute pipeline tasks
                click.echo("\n🚀 Starting pipeline execution...")
                
                # First run the read task to analyze the website
                read_task = pipeline_tasks[0]
                click.echo(f"\n📖 Running initial website analysis...")
                read_result = await system.process_task(read_task["task_type"], read_task["data"])
                if read_result["status"] != "success":
                    raise Exception(f"Read task failed: {read_result.get('message', 'Unknown error')}")
                click.echo("✅ Website analysis completed")

                # Process specialized agent tasks
                for task in pipeline_tasks[1:]:
                    click.echo(f"\n🔄 Processing {task['task_type']}...")
                    result = await system.process_task(task["task_type"], task["data"])
                    
                    if result["status"] != "success":
                        click.echo(f"⚠️  Task {task['task_type']} failed: {result.get('message', 'Unknown error')}")
                        continue
                        
                    click.echo(f"✅ {task['task_type']} completed successfully")

                    # Notify CI/CD agent of task completion
                    cicd_result = await system.process_task("cicd_deployment", {
                        "task_type": task["task_type"]
                    })
                    click.echo(f"📬 CI/CD agent notified for {task['task_type']}")

                click.echo("\n🔍 CI/CD agent is now:")
                click.echo("1. Running old version (main branch) on port 3000")
                click.echo("2. Running new version (sitesentry branch) on port 3001")
                click.echo("3. Running auditor tool on both versions")
                click.echo("4. Comparing results and either:")
                click.echo("   - Creating a pull request if improvements are verified")
                click.echo("   - Notifying manager agent if further improvements needed")

                # Wait for deployment checks to complete
                click.echo("\n⏳ Waiting for deployment checks to complete...")
                await asyncio.sleep(5)  # Give time for deployment checks

                click.echo("\n✨ Pipeline execution completed!")
                
            except Exception as e:
                logger.error("pipeline_error", error=str(e))
                click.echo(f"\n❌ Pipeline execution failed: {str(e)}", err=True)
                raise
            finally:
                # Cleanup
                await system.cleanup()
                click.echo("\n🧹 System cleanup completed")

        # Run the pipeline
        asyncio.run(run_pipeline())
            
    except Exception as e:
        logger.error("run_error", error=str(e))
        click.echo(f"Error running pipeline: {str(e)}", err=True)

@cli.command()
def dev():
    """Run AgentX in development mode."""
    try:
        # Ensure environment variables are loaded
        load_dotenv()
        
        # Debug: Check if environment variable is loaded
        click.echo(f"GOOGLE_API_KEY loaded: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
        
        # Load configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            click.echo("Configuration file not found. Run 'python -m agentx.cli init' first.", err=True)
            return
        
        # Initialize system
        system = AgentXSystem(str(config_path))
        asyncio.run(system.initialize())
        
        click.echo("Starting development server...")
        # Start the development server with auto-reload
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
        click.echo(f"Error starting development server: {str(e)}", err=True)

@cli.command()
@click.option("--output", "-o", default="dist", help="Output directory for built files")
def build(output: str):
    """Build AgentX for production."""
    try:
        # Validate configuration
        config_path = Path("config/agentx.config.yaml")
        if not config_path.exists():
            click.echo("Configuration file not found. Run 'python -m agentx.cli init' first.", err=True)
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
        
        for file_path in files_to_copy:
            src = Path(file_path)
            if src.exists():
                if src.is_dir():
                    shutil.copytree(src, output_dir / src.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, output_dir / src.name)
                click.echo(f"Copied: {file_path}")
            else:
                click.echo(f"Warning: {file_path} not found", err=True)
        
        click.echo(f"\nBuild complete! Output directory: {output_dir}")
        
    except Exception as e:
        logger.error("build_error", error=str(e))
        click.echo(f"Error building project: {str(e)}", err=True)

if __name__ == '__main__':
    cli() 