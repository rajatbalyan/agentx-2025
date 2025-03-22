import os
from controller import GitHubController 
from dotenv import load_dotenv 

load_dotenv()



gh = GitHubController(
    token=os.getenv("GITHUB_TOKEN"), 
    repo_owner="ShubhamTiwary914", 
    repo_name="boiler-metaMQTT")



gh.register_self_hosted_runner("test-runner")


