"""Test file for GitHub controller."""

import os
from datetime import datetime
from .controller import GitHubController
from dotenv import load_dotenv

load_dotenv()


def test_github_controller():
    """Test the GitHub controller functionality."""
    # Get GitHub token from environment
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
    print("GitHub token loaded successfully")
    
    # Initialize controller
    controller = GitHubController(
        token=token,
        repo_owner="metacatalyst",
        repo_name="landing-page"
    )
    
    # Ensure we're on the sitesentry branch
    result = controller.ensure_sitesentry_branch()
    if result["status"] != "success":
        raise RuntimeError(f"Failed to setup sitesentry branch: {result['message']}")
    
    print(f"Successfully set up branch: {result['branch']}")
    
    # Make some test changes
    test_file = "test.txt"
    with open(test_file, "w") as f:
        f.write(f"Test change at {datetime.now()}")
    
    # Commit and push changes
    if not controller.commit_changes("Test commit from AgentX"):
        raise RuntimeError("Failed to commit changes")
    
    if not controller.push_changes():
        raise RuntimeError("Failed to push changes")
    
    print("Successfully committed and pushed changes to sitesentry branch")
    
    # Clean up test file
    os.remove(test_file)
    return controller.SITESENTRY_BRANCH

if __name__ == "__main__":
    test_github_controller()


