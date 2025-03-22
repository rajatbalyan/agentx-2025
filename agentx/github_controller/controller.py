#Controller for the GitHub API - Actions, Pull Requests, etc.

import os
import requests
import subprocess
from typing import Optional, Dict, List
import structlog

logger = structlog.get_logger()

class GitHubController:
    SITESENTRY_BRANCH = "sitesentry-test-branch"

    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        Initialize the GitHub controller with the personal access token, repo owner, and repo name
        """
        self.token = token  #personal access token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    
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

    def checkout_branch(self, branch_name: str, create: bool = False) -> bool:
        """
        Checkout a Git branch. Optionally create it if it doesn't exist.
        Returns True if successful, False otherwise.
        """
        try:
            if create:
                # First check if branch exists
                result = subprocess.run(
                    ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                    capture_output=True
                )
                
                if result.returncode == 0:
                    # Branch exists, just checkout
                    subprocess.run(["git", "checkout", branch_name], check=True)
                else:
                    # Create and checkout new branch
                    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            else:
                subprocess.run(["git", "checkout", branch_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Failed to checkout branch", branch=branch_name, error=str(e))
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
            subprocess.run(["git", "pull", "origin", base_branch], check=True)
            
            # Create and checkout new branch
            if not self.checkout_branch(branch_name, create=True):
                return {"status": "error", "message": f"Failed to create branch {branch_name}"}
            
            # Push the new branch to remote
            try:
                subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
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

    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> bool:
        """
        Commit changes to the current branch.
        If files is None, commits all changes.
        """
        try:
            if files:
                # Add specific files
                for file in files:
                    subprocess.run(["git", "add", file], check=True)
            else:
                # Add all changes
                subprocess.run(["git", "add", "."], check=True)
            
            # Commit changes
            subprocess.run(["git", "commit", "-m", message], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Failed to commit changes", error=str(e))
            return False

    def register_self_hosted_runner(self, runner_name: str) -> dict:
        """
        Register a self-hosted runner
        Args:
            runner_name (str): Name for the runner 
        Returns:
            dict: Response from the registration process
        """
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
        
        try:
            subprocess.run(docker_command, check=True)
            return {"status": "success", "runner_name": runner_name}
        except subprocess.CalledProcessError as e:
            return {"status": "error", "message": str(e)}

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists locally or remotely."""
        try:
            # Check local branch
            local_result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                capture_output=True
            )
            if local_result.returncode == 0:
                return True

            # Check remote branch
            remote_result = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", branch_name],
                capture_output=True,
                text=True
            )
            return bool(remote_result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def ensure_sitesentry_branch(self) -> dict:
        """
        Ensure the sitesentry test branch exists and we're on it.
        Creates it if it doesn't exist.
        """
        try:
            # Check if we're already on the sitesentry branch
            current = self.get_current_branch()
            if current == self.SITESENTRY_BRANCH:
                return {
                    "status": "success",
                    "message": f"Already on {self.SITESENTRY_BRANCH}",
                    "branch": self.SITESENTRY_BRANCH
                }

            # Check if branch exists
            if self.branch_exists(self.SITESENTRY_BRANCH):
                # Branch exists, just checkout
                if not self.checkout_branch(self.SITESENTRY_BRANCH):
                    return {
                        "status": "error",
                        "message": f"Failed to checkout existing {self.SITESENTRY_BRANCH}"
                    }
            else:
                # Create new branch from main
                result = self.create_branch(self.SITESENTRY_BRANCH, "main")
                if result["status"] != "success":
                    return result

            return {
                "status": "success",
                "message": f"Successfully set up {self.SITESENTRY_BRANCH}",
                "branch": self.SITESENTRY_BRANCH
            }

        except Exception as e:
            logger.error("Failed to ensure sitesentry branch", error=str(e))
            return {"status": "error", "message": str(e)}

    def push_changes(self) -> bool:
        """Push changes to the current branch."""
        try:
            current = self.get_current_branch()
            subprocess.run(["git", "push", "origin", current], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Failed to push changes", error=str(e))
            return False
    
    

    