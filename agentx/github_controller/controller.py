#Controller for the GitHub API - Actions, Pull Requests, etc.


import requests
import subprocess



class GitHubController:
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
            Initialize the GitHub controller with the personal access token, repo owner, and repo name
        """
        self.token = token  #personal access token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
       
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> dict:
        """
            Create a new branch from the base branch
        """
        pass
    
    def create_pull_request(self, branch_name: str, title: str, body: str = "") -> dict:
        """
            Create a new pull request
        """
        pass 

    def register_self_hosted_runner(self, runner_name: str) -> dict:
        """
            Register a self-hosted runner
            Args:
                runner_name (str): Name for the runner 
            Returns:
                dict: Response from the registration process
        """
        # Get runner registration token
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        response = requests.post(
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/actions/runners/registration-token",
            headers=headers
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
    
    

    