"""Controller for the GitHub API - Actions, Pull Requests, etc."""

import os
import requests
import subprocess
from typing import Optional, Dict, List, Any
import structlog

logger = structlog.get_logger()

class GitHubController:
    SITESENTRY_BRANCH = "sitesentry-test-branch"

    def __init__(self, token: str, repo_owner: str, repo_name: str, workspace_path: str = None):
        """
        Initialize the GitHub controller with the personal access token, repo owner, and repo name
        """
        self.token = token  #personal access token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.workspace_path = workspace_path or "."
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.logger = structlog.get_logger().bind(component="github_controller")
    
    def get_current_branch(self) -> str:
        """Get the name of the current Git branch."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error("Failed to get current branch", error=str(e))
            raise RuntimeError("Failed to get current branch") from e

    def run_git_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command.
        
        Args:
            command: Git command as list of strings
            check: Whether to check return code
            
        Returns:
            CompletedProcess instance
        """
        try:
            full_command = ["git"] + command
            result = subprocess.run(
                full_command,
                cwd=self.workspace_path,
                check=check,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(
                "Git command failed",
                command=command,
                error=str(e),
                stdout=e.stdout,
                stderr=e.stderr
            )
            raise

    def stash_changes(self) -> bool:
        """Stash any local changes.
        
        Returns:
            bool: True if stashing was successful
        """
        try:
            result = self.run_git_command(["stash", "save", "Temporary stash before branch switch"])
            return result.returncode == 0
        except Exception as e:
            logger.error("Failed to stash changes", error=str(e))
            return False

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout a branch, stashing changes if needed.
        
        Args:
            branch_name: Name of branch to checkout
            
        Returns:
            bool: True if checkout was successful
        """
        try:
            # First try to checkout
            try:
                self.run_git_command(["checkout", branch_name])
                logger.info("Checked out branch", branch=branch_name)
                return True
            except subprocess.CalledProcessError:
                # If checkout fails, try stashing first
                if self.stash_changes():
                    try:
                        self.run_git_command(["checkout", branch_name])
                        logger.info("Checked out branch after stashing", branch=branch_name)
                        return True
                    except subprocess.CalledProcessError as e:
                        logger.error(
                            "Failed to checkout branch even after stashing",
                            branch=branch_name,
                            error=str(e)
                        )
                        return False
                else:
                    logger.error("Failed to stash changes before checkout", branch=branch_name)
                    return False
        except Exception as e:
            logger.error("Error during branch checkout", branch=branch_name, error=str(e))
            return False
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> dict:
        """
        Create a new branch from the base branch both locally and remotely
        """
        try:
            # First ensure we're on the base branch
            current = self.get_current_branch()
            if current != base_branch:
                if not self.checkout_branch(base_branch):
                    return {"status": "error", "message": f"Failed to checkout {base_branch}"}
            
            # Pull latest changes
            self.run_git_command(["pull", "origin", base_branch])
            
            # Create and checkout new branch
            if not self.checkout_branch(branch_name):
                return {"status": "error", "message": f"Failed to create branch {branch_name}"}
            
            # Push the new branch to remote
            try:
                self.run_git_command(["push", "-u", "origin", branch_name])
            except subprocess.CalledProcessError:
                # If remote push fails, it's not critical for local development
                logger.warning("Failed to push branch to remote", branch=branch_name)
            
            return {
                "status": "success",
                "message": f"Created and checked out branch {branch_name}",
                "branch": branch_name
            }
            
        except Exception as e:
            logger.error("Failed to create branch", branch=branch_name, error=str(e))
            return {"status": "error", "message": str(e)}
    
    def create_pull_request(self, branch_name: str, title: str, body: str = "") -> dict:
        """
        Create a new pull request from the specified branch to main
        """
        try:
            data = {
                "title": title,
                "body": body,
                "head": branch_name,
                "base": "main"
            }
            
            response = requests.post(
                f"{self.base_url}/pulls",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            
            pr_data = response.json()
            return {
                "status": "success",
                "message": "Pull request created successfully",
                "pr_number": pr_data["number"],
                "pr_url": pr_data["html_url"]
            }
        except Exception as e:
            logger.error("Failed to create pull request", branch=branch_name, error=str(e))
            return {"status": "error", "message": str(e)}

    def commit_changes(self, message: str, files: List[str] = None) -> bool:
        """Commit changes to the repository.
        
        Args:
            message: Commit message
            files: List of files to commit, or None for all changes
            
        Returns:
            bool: True if successful
        """
        try:
            # Add files
            if files:
                for file in files:
                    self.run_git_command(["add", file])
            else:
                self.run_git_command(["add", "."])
            
            # Check if there are changes to commit
            status = self.run_git_command(["status", "--porcelain"])
            if not status.stdout.strip():
                self.logger.info("No changes to commit")
                return True
                
            # Commit changes
            self.run_git_command(["commit", "-m", message])
            return True
        except Exception as e:
            self.logger.error("Failed to commit changes", error=str(e))
            return False

    def register_self_hosted_runner(self, runner_name: str) -> dict:
        """
        Register a self-hosted runner
        Args:
            runner_name (str): Name for the runner 
        Returns:
            dict: Response from the registration process
        """
        try:
            # Get runner registration token
            response = requests.post(
                f"{self.base_url}/actions/runners/registration-token",
                headers=self.headers
            )
            
            registration_data = response.json()
            runner_token = registration_data['token']
            
            docker_command = [
                "docker", "run", "-d", "--restart", "always",
                f"--name={runner_name}",
                "-e", f"REPO_URL=https://github.com/{self.repo_owner}/{self.repo_name}",
                "-e", f"RUNNER_NAME={runner_name}",
                "-e", f"RUNNER_TOKEN={runner_token}",
                "-e", "RUNNER_WORKDIR=/tmp/runner/work",
                "myoung34/github-runner:latest"
            ]
            
            self.run_git_command(docker_command, check=True)
            return {"status": "success", "runner_name": runner_name}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists locally or remotely."""
        try:
            # First check local branches
            try:
                result = self.run_git_command(["rev-parse", "--verify", branch_name])
                if result.returncode == 0:
                    return True
            except subprocess.CalledProcessError:
                pass
            
            # Then check remote branches
            try:
                result = self.run_git_command(["ls-remote", "--heads", "origin", branch_name])
                return bool(result.stdout.strip())
            except subprocess.CalledProcessError:
                pass
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to check branch existence", branch=branch_name, error=str(e))
            return False

    def ensure_git_initialized(self) -> bool:
        """Ensure Git repository is initialized.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Check if .git directory exists
            if not os.path.exists(os.path.join(self.workspace_path, ".git")):
                self.logger.info("Initializing Git repository", workspace=self.workspace_path)
                
                # Initialize repository
                self.run_git_command(["init"])
                
                # Configure user if not set
                try:
                    self.run_git_command(["config", "user.email", "agentx@example.com"])
                    self.run_git_command(["config", "user.name", "AgentX"])
                except subprocess.CalledProcessError:
                    self.logger.warning("Failed to configure Git user")
                
                # Configure remote if needed
                try:
                    remote_url = f"https://{self.token}@github.com/{self.repo_owner}/{self.repo_name}.git"
                    self.run_git_command(["remote", "add", "origin", remote_url])
                except subprocess.CalledProcessError:
                    # Remote might already exist, try to update it
                    try:
                        self.run_git_command(["remote", "set-url", "origin", remote_url])
                    except subprocess.CalledProcessError:
                        self.logger.error("Failed to configure remote")
                        return False
                
                # Try to fetch from remote
                try:
                    self.run_git_command(["fetch", "origin"], check=False)
                except subprocess.CalledProcessError:
                    self.logger.warning("Failed to fetch from remote")
                
                # Make initial commit if needed
                try:
                    status = self.run_git_command(["status", "--porcelain"])
                    if status.stdout.strip():
                        self.run_git_command(["add", "."])
                        self.run_git_command(["commit", "-m", "Initial commit"])
                except subprocess.CalledProcessError:
                    self.logger.warning("Failed to make initial commit")
                
                self.logger.info("Git repository initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Git repository", error=str(e))
            return False

    def ensure_sitesentry_branch(self) -> Dict[str, Any]:
        """Ensure sitesentry branch exists and is checked out.
        
        Returns:
            Dict with status and branch information
        """
        try:
            # First ensure Git is initialized
            if not self.ensure_git_initialized():
                return {
                    "status": "error",
                    "message": "Failed to initialize Git repository"
                }
            
            # Try to fetch latest changes
            try:
                self.run_git_command(["fetch", "origin"], check=False)
            except subprocess.CalledProcessError:
                self.logger.warning("Failed to fetch from remote")
            
            # Check if branch exists locally or remotely
            branch_exists = self.branch_exists(self.SITESENTRY_BRANCH)
            
            if not branch_exists:
                # Create new branch from current HEAD
                try:
                    self.run_git_command(["checkout", "-b", self.SITESENTRY_BRANCH])
                    self.logger.info("Created new branch", branch=self.SITESENTRY_BRANCH)
                    
                    # Try to push the new branch
                    try:
                        self.run_git_command(["push", "-u", "origin", self.SITESENTRY_BRANCH], check=False)
                    except subprocess.CalledProcessError:
                        self.logger.warning("Failed to push new branch to remote", branch=self.SITESENTRY_BRANCH)
                    
                except subprocess.CalledProcessError as e:
                    error_msg = f"Failed to create branch {self.SITESENTRY_BRANCH}: {str(e)}"
                    self.logger.error(error_msg)
                    return {
                        "status": "error",
                        "message": error_msg
                    }
            else:
                # Try to checkout existing branch
                if not self.checkout_branch(self.SITESENTRY_BRANCH):
                    return {
                        "status": "error",
                        "message": f"Failed to checkout {self.SITESENTRY_BRANCH}"
                    }
                
                # Try to pull latest changes
                try:
                    self.run_git_command(["pull", "origin", self.SITESENTRY_BRANCH], check=False)
                except subprocess.CalledProcessError:
                    self.logger.warning("Failed to pull latest changes", branch=self.SITESENTRY_BRANCH)
            
            return {
                "status": "success",
                "branch_name": self.SITESENTRY_BRANCH,
                "message": f"Successfully set up {self.SITESENTRY_BRANCH} branch"
            }
            
        except Exception as e:
            error_msg = f"Failed to ensure {self.SITESENTRY_BRANCH} branch: {str(e)}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg
            }

    def push_changes(self) -> bool:
        """Push changes to remote repository.
        
        Returns:
            bool: True if successful
        """
        try:
            current = self.get_current_branch()
            self.run_git_command(["push", "origin", current])
            return True
        except Exception as e:
            self.logger.error("Failed to push changes", error=str(e))
            return False
    
    

    