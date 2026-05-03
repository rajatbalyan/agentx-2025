# site_sentry/cli/commands.py
"""
Site-Sentry CLI — `sentry` command.
Commands: init, run, status
"""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from typing import Optional

import click
import structlog
import yaml
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger()


def _configure_logging(level: str, log_file: Optional[str] = None) -> None:
    """Configure structlog for CLI output."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
    )


@click.group()
@click.version_option(version="1.0.0", prog_name="sentry")
def cli():
    """
    Site-Sentry — Autonomous website maintenance agent.

    Audits your live site with Lighthouse and automatically opens a GitHub PR
    with fixes for SEO, performance, accessibility, and errors.

    Quick start:
      sentry init          # Create config file
      sentry run           # Run full pipeline
      sentry run --dry-run # Preview changes without committing
    """
    pass


@cli.command()
@click.option(
    "--url", prompt="Target website URL", help="URL of the live website to audit"
)
@click.option(
    "--workspace", default=".", help="Path to the local repo (default: current dir)"
)
@click.option("--github-owner", default="", help="GitHub username or org")
@click.option("--github-repo", default="", help="GitHub repo name")
def init(url: str, workspace: str, github_owner: str, github_repo: str):
    """Initialize Site-Sentry in the current directory."""
    config_path = Path("sentry.config.yaml")

    if config_path.exists():
        if not click.confirm("sentry.config.yaml already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    # Load template
    template_path = (
        Path(__file__).parent.parent / "config" / "sentry.config.yaml.template"
    )
    with open(template_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Apply user inputs
    config["website_url"] = url
    config["workspace_path"] = str(Path(workspace).resolve())
    if github_owner:
        config["github"]["repo_owner"] = github_owner
    if github_repo:
        config["github"]["repo_name"] = github_repo

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # Create required directories
    for d in ["logs", "data/memory/vectors", "temp/lighthouse"]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Create .env if missing
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(
            "# NVIDIA NIM API key - get free key at https://build.nvidia.com\n"
            "NVIDIA_API_KEY=nvapi-your-key-here\n\n"
            "# GitHub Personal Access Token (repo scope)\n"
            "GITHUB_TOKEN=ghp_your-token-here\n",
            encoding="utf-8",
        )
        click.echo("Created .env template")

        click.echo(click.style("\n[OK] Site-Sentry initialized!", fg="green"))
    click.echo(f"   Config:    {config_path}")
    click.echo(f"   Target:    {url}")
    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Edit .env and add your NVIDIA_API_KEY and GITHUB_TOKEN")
    click.echo("  2. Install Lighthouse: npm install -g lighthouse")
    click.echo("  3. Run: sentry run")


@cli.command()
@click.option(
    "--config",
    "config_path",
    default="sentry.config.yaml",
    help="Path to config file (default: sentry.config.yaml)",
)
@click.option("--url", default=None, help="Override the target URL from config")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Audit and generate fixes but do NOT commit or open a PR",
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Verbose logging"
)
def run(config_path: str, url: Optional[str], dry_run: bool, verbose: bool):
    """
    Run the full Site-Sentry pipeline.

    Audits your website → generates fixes → commits to a new branch → opens a PR.
    Use --dry-run to preview without committing.
    """
    from site_sentry.config.schema import SentryConfig
    from site_sentry.pipeline import SentryPipeline

    try:
        config = SentryConfig.load(config_path)
    except FileNotFoundError as e:
        click.echo(click.style(f"[X] {e}", fg="red"))
        return

    _configure_logging("DEBUG" if verbose else config.logging.level)

    # Preflight checks
    if not config.api_key:
        click.echo(click.style("[X] NVIDIA_API_KEY not set in .env", fg="red"))
        click.echo("   Get a free key at: https://build.nvidia.com")
        return

    if not dry_run and not config.github_token:
        click.echo(
            click.style(
                "[!] GITHUB_TOKEN not set — running in dry-run mode", fg="yellow"
            )
        )
        dry_run = True

    mode_label = (
        click.style("DRY RUN", fg="yellow")
        if dry_run
        else click.style("LIVE", fg="green")
    )
    target = url or config.website_url

    click.echo(f"\n[*] Site-Sentry [{mode_label}]")
    click.echo(f"   Target : {target}")
    click.echo(f"   Model  : {config.llm.manager_model} (manager)")
    click.echo(f"            {config.llm.agent_model} (agents)")
    click.echo("")

    pipeline = SentryPipeline(config)

    try:
        result = asyncio.run(pipeline.run(url=url, dry_run=dry_run))
    except KeyboardInterrupt:
        click.echo("\nAborted by user.")
        return

    # Print results
    if result["status"] == "error":
        click.echo(
            click.style(f"\n[X] Pipeline failed: {result['error']}", fg="red")
        )
        return

    click.echo(click.style("\n[OK] Pipeline complete!", fg="green"))
    if result.get("message"):
        click.echo(f"   {result['message']}")
    click.echo(f"   Duration : {result.get('duration_seconds', 0)}s")
    click.echo(f"   Agents   : {', '.join(result.get('agents_run', []))}")
    click.echo(f"   Changes  : {result.get('changes', 0)} files")

    if result.get("pr"):
        click.echo(f"   PR       : {result['pr']['url']}")
    elif dry_run:
        click.echo(click.style("   [Dry run - no PR created]", fg="yellow"))
    elif result.get("mode") in ("dry-run", "no-github"):
        click.echo(
            click.style(
                f"   [{result['mode']}: no PR created — see summary above]",
                fg="yellow",
            )
        )


@cli.command()
@click.option("--config", "config_path", default="sentry.config.yaml")
def status(config_path: str):
    """Check configuration and connectivity status."""
    import shutil

    from site_sentry.config.schema import SentryConfig

    click.echo("\n[*] Site-Sentry Status Check")
    click.echo("=" * 40)

    # Config
    try:
        config = SentryConfig.load(config_path)
        click.echo(
            click.style("[OK] Config loaded", fg="green") + f" ({config_path})"
        )
        click.echo(f"   Target: {config.website_url}")
    except Exception as e:
        click.echo(click.style(f"[X] Config: {e}", fg="red"))
        return

    # API Key
    if config.api_key:
        click.echo(click.style("[OK] NVIDIA_API_KEY set", fg="green"))
    else:
        click.echo(click.style("[X] NVIDIA_API_KEY missing", fg="red"))

    # GitHub
    if config.github_token:
        click.echo(click.style("[OK] GITHUB_TOKEN set", fg="green"))
    else:
        click.echo(
            click.style("[!] GITHUB_TOKEN missing (dry-run only)", fg="yellow")
        )

    # Node.js + Lighthouse
    if shutil.which("node"):
        click.echo(click.style("[OK] Node.js found", fg="green"))
    else:
        click.echo(
            click.style("[X] Node.js not found - install from nodejs.org", fg="red")
        )

    if shutil.which("lighthouse"):
        click.echo(click.style("[OK] Lighthouse found", fg="green"))
    else:
        click.echo(
            click.style(
                "[X] Lighthouse not found - run: npm install -g lighthouse",
                fg="red",
            )
        )

    click.echo("")


if __name__ == "__main__":
    cli()
