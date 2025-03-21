from typing import Dict, Any, List
import asyncio
from datetime import datetime
import os
from github import Github
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig

class CICDDeploymentAgent(BaseAgent):
    """Agent responsible for CI/CD and deployment processes"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.github = Github(os.getenv("GITHUB_TOKEN"))
        self.repo = self.github.get_repo(os.getenv("GITHUB_REPO"))
        self.test_branch_prefix = "test-"
        self.main_branch = "main"
    
    async def create_test_branch(
        self,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a test branch for proposed changes"""
        try:
            # Generate branch name
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"{self.test_branch_prefix}{timestamp}"
            
            # Get main branch reference
            main_ref = self.repo.get_git_ref(f"heads/{self.main_branch}")
            
            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=main_ref.object.sha
            )
            
            # Create commits for changes
            for file_path, content in changes.items():
                try:
                    # Get current file if exists
                    try:
                        current_file = self.repo.get_contents(
                            file_path,
                            ref=branch_name
                        )
                        # Update file
                        self.repo.update_file(
                            file_path,
                            f"Update {file_path}",
                            content,
                            current_file.sha,
                            branch=branch_name
                        )
                    except:
                        # Create new file
                        self.repo.create_file(
                            file_path,
                            f"Create {file_path}",
                            content,
                            branch=branch_name
                        )
                except Exception as e:
                    self.logger.error("file_update_error", file=file_path, error=str(e))
            
            return {
                "status": "success",
                "branch_name": branch_name
            }
            
        except Exception as e:
            self.logger.error("branch_creation_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_tests(
        self,
        branch_name: str
    ) -> Dict[str, Any]:
        """Run tests on the test branch"""
        try:
            # Get test workflow
            workflow = self.repo.get_workflow("test.yml")
            
            # Trigger workflow
            run = workflow.create_dispatch(
                branch_name,
                inputs={"environment": "test"}
            )
            
            # Wait for workflow completion
            while True:
                run = self.repo.get_workflow_run(run.id)
                if run.status == "completed":
                    break
                await asyncio.sleep(10)
            
            return {
                "status": "success" if run.conclusion == "success" else "failed",
                "details": {
                    "run_id": run.id,
                    "conclusion": run.conclusion,
                    "url": run.html_url
                }
            }
            
        except Exception as e:
            self.logger.error("test_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def create_pull_request(
        self,
        branch_name: str,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create pull request for the changes"""
        try:
            # Generate PR title and body
            title = f"Updates from {branch_name}"
            body = "Automated updates from AgentX\n\nChanges:\n"
            for file_path in changes.keys():
                body += f"- Modified {file_path}\n"
            
            # Create pull request
            pr = self.repo.create_pull(
                title=title,
                body=body,
                base=self.main_branch,
                head=branch_name
            )
            
            return {
                "status": "success",
                "pr_number": pr.number,
                "pr_url": pr.html_url
            }
            
        except Exception as e:
            self.logger.error("pr_creation_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def deploy_to_production(
        self,
        pr_number: int
    ) -> Dict[str, Any]:
        """Deploy changes to production"""
        try:
            # Get pull request
            pr = self.repo.get_pull(pr_number)
            
            # Check if PR is approved and tests pass
            if not pr.mergeable:
                return {
                    "status": "error",
                    "error": "Pull request is not mergeable"
                }
            
            # Merge pull request
            merge_result = pr.merge()
            
            if merge_result.merged:
                # Trigger production deployment workflow
                workflow = self.repo.get_workflow("deploy.yml")
                run = workflow.create_dispatch(
                    self.main_branch,
                    inputs={"environment": "production"}
                )
                
                # Wait for deployment completion
                while True:
                    run = self.repo.get_workflow_run(run.id)
                    if run.status == "completed":
                        break
                    await asyncio.sleep(10)
                
                return {
                    "status": "success",
                    "details": {
                        "run_id": run.id,
                        "conclusion": run.conclusion,
                        "url": run.html_url
                    }
                }
            
            return {
                "status": "error",
                "error": "Failed to merge pull request"
            }
            
        except Exception as e:
            self.logger.error("deployment_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment request"""
        action = data.get("action")
        if not action:
            raise ValueError("Action is required")
        
        try:
            if action == "create_test_branch":
                result = await self.create_test_branch(data.get("changes", {}))
            
            elif action == "run_tests":
                result = await self.run_tests(data["branch_name"])
            
            elif action == "create_pr":
                result = await self.create_pull_request(
                    data["branch_name"],
                    data.get("changes", {})
                )
            
            elif action == "deploy":
                result = await self.deploy_to_production(data["pr_number"])
            
            else:
                raise ValueError(f"Unknown action: {action}")
            
            # Store deployment action in memory
            await self.memory_manager.add_document({
                "action": action,
                "data": data,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            self.logger.error("processing_error", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        await super().cleanup() 