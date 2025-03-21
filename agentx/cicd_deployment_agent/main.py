import asyncio
from typing import Dict, Any, List
import os
from datetime import datetime
from github import Github
from pydantic import BaseModel
import docker
import tempfile
import shutil

from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class DeploymentConfig(BaseModel):
    """Configuration for deployment"""
    github_token: str
    repository: str
    base_branch: str = "main"
    staging_url: str = "http://staging.example.com"
    production_url: str = "http://example.com"

class DeploymentAgent(BaseAgent):
    """Agent responsible for deploying changes through CI/CD pipeline"""
    
    async def initialize(self) -> None:
        """Initialize GitHub and Docker clients"""
        self.config = DeploymentConfig(
            github_token=os.getenv("GITHUB_TOKEN"),
            repository=os.getenv("GITHUB_REPOSITORY")
        )
        
        self.github = Github(self.config.github_token)
        self.repo = self.github.get_repo(self.config.repository)
        self.docker_client = docker.from_url("unix://var/run/docker.sock")
        
        # Create temporary directory for file operations
        self.temp_dir = tempfile.mkdtemp()
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.github.close()
        shutil.rmtree(self.temp_dir)
    
    async def create_branch(self, changes: List[Dict[str, Any]]) -> str:
        """Create a new branch for the changes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"auto_update_{timestamp}"
        
        # Create new branch from main
        source = self.repo.get_branch(self.config.base_branch)
        self.repo.create_git_ref(
            ref=f"refs/heads/{branch_name}",
            sha=source.commit.sha
        )
        
        return branch_name
    
    async def commit_changes(
        self,
        branch: str,
        changes: List[Dict[str, Any]]
    ) -> None:
        """Commit changes to the branch"""
        for change in changes:
            file_path = change['file_path']
            content = change['content']
            message = change['commit_message']
            
            try:
                # Get current file if it exists
                file = self.repo.get_contents(file_path, ref=branch)
                self.repo.update_file(
                    file_path,
                    message,
                    content,
                    file.sha,
                    branch=branch
                )
            except Exception:
                # File doesn't exist, create it
                self.repo.create_file(
                    file_path,
                    message,
                    content,
                    branch=branch
                )
    
    async def run_tests(self, branch: str) -> bool:
        """Run tests in a staging environment"""
        try:
            # Clone repository to temp directory
            repo_path = os.path.join(self.temp_dir, "repo")
            os.system(f"git clone -b {branch} {self.config.repository} {repo_path}")
            
            # Build and run tests in Docker
            self.docker_client.images.build(
                path=repo_path,
                tag="staging_test"
            )
            
            container = self.docker_client.containers.run(
                "staging_test",
                command=["pytest"],
                detach=True
            )
            
            # Wait for tests to complete
            result = container.wait()
            logs = container.logs().decode()
            
            # Cleanup
            container.remove()
            
            return result['StatusCode'] == 0
            
        except Exception as e:
            self.logger.error("test_error", error=str(e))
            return False
    
    async def create_pull_request(
        self,
        branch: str,
        changes: List[Dict[str, Any]]
    ) -> None:
        """Create a pull request for the changes"""
        # Generate PR description from changes
        description = "Automated updates by AgentX\n\nChanges:\n"
        for change in changes:
            description += f"- {change['commit_message']}\n"
        
        self.repo.create_pull(
            title=f"Automated updates {datetime.now().strftime('%Y-%m-%d')}",
            body=description,
            base=self.config.base_branch,
            head=branch
        )
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment request"""
        changes = data.get('changes', [])
        if not changes:
            return {
                "status": "error",
                "message": "No changes provided"
            }
        
        try:
            # Create new branch
            branch = await self.create_branch(changes)
            
            # Commit changes
            await self.commit_changes(branch, changes)
            
            # Run tests
            tests_passed = await self.run_tests(branch)
            
            if tests_passed:
                # Create pull request
                await self.create_pull_request(branch, changes)
                return {
                    "status": "success",
                    "message": "Pull request created successfully",
                    "branch": branch
                }
            else:
                return {
                    "status": "error",
                    "message": "Tests failed",
                    "branch": branch
                }
                
        except Exception as e:
            self.logger.error("deployment_error", error=str(e))
            return {
                "status": "error",
                "message": str(e)
            }

if __name__ == "__main__":
    config = AgentConfig(
        name="cicd_deployment_agent",
        port=8007
    )
    
    agent = DeploymentAgent(config)
    agent.start() 