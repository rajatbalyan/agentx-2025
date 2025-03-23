"""CI/CD Deployment Agent for managing deployments and quality checks."""

import os
import asyncio
import subprocess
import platform
import signal
import psutil
from typing import Dict, Any, List
import structlog
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig
from agentx.github_controller.controller import GitHubController

logger = structlog.get_logger()

class CICDDeploymentAgent(BaseAgent):
    """Agent responsible for CI/CD deployment and quality checks."""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        """Initialize the CI/CD Deployment Agent.
        
        Args:
            config: Agent configuration
            system_config: System configuration
        """
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="cicd_deployment")
        self.github = GitHubController(
            token=system_config.api_keys.get('github_token', ''),
            repo_owner=system_config.github.repo_owner,
            repo_name=system_config.github.repo_name,
            workspace_path=system_config.workspace.path
        )
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment tasks.
        
        Args:
            data: Task data containing changes to push
            
        Returns:
            Processing results
        """
        try:
            # Ensure we're on the sitesentry branch
            result = self.github.ensure_sitesentry_branch()
            if result["status"] != "success":
                return {
                    "status": "error",
                    "error": f"Failed to switch to sitesentry branch: {result['message']}"
                }
            
            branch_name = result.get("branch_name", self.github.SITESENTRY_BRANCH)
            self.logger.info("Working on branch", branch=branch_name)
            
            # Commit changes if there are any
            if not self.github.commit_changes(f"Update from SiteSentry on {branch_name}"):
                return {
                    "status": "error",
                    "error": "Failed to commit changes"
                }
            
            # Push changes to remote
            if not self.github.push_changes():
                return {
                    "status": "error",
                    "error": "Failed to push changes"
                }
            
            return {
                "status": "success",
                "message": f"Changes pushed to {branch_name}",
                "branch": branch_name
            }
            
        except Exception as e:
            self.logger.error("Error processing deployment task", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop any running servers
            if hasattr(self, 'old_server') and self.old_server:
                try:
                    self.old_server.terminate()
                    self.old_server = None
                    self.logger.info("Old server terminated")
                except Exception as e:
                    self.logger.error("Failed to terminate old server", error=str(e))
            
            if hasattr(self, 'new_server') and self.new_server:
                try:
                    self.new_server.terminate()
                    self.new_server = None
                    self.logger.info("New server terminated")
                except Exception as e:
                    self.logger.error("Failed to terminate new server", error=str(e))
            
            # Clean up temporary files
            if hasattr(self, 'temp_dir') and self.temp_dir:
                try:
                    import shutil
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                    self.logger.info("Temporary directory cleaned up")
                except Exception as e:
                    self.logger.error("Failed to clean up temporary directory", error=str(e))
            
            await super().cleanup()
            self.logger.info("CICD deployment agent cleaned up")
            
        except Exception as e:
            self.logger.error("Error during CICD deployment cleanup", error=str(e)) 