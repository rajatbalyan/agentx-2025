"""Full system test for AgentX."""

import os
import asyncio
from agentx.system import AgentXSystem
from agentx.common_libraries.system_config import SystemConfig

async def test_full_system():
    """Run a full system test."""
    try:
        # Initialize the system
        system = AgentXSystem()
        await system.initialize()
        print("✅ System initialized successfully")

        # Simulate content changes by specialized agents
        changes = [
            {
                "task_type": "performance_monitoring",
                "changes": {
                    "type": "performance_optimization",
                    "files_modified": ["src/components/Hero.tsx"],
                    "description": "Optimized image loading in Hero component"
                }
            },
            {
                "task_type": "seo_optimization",
                "changes": {
                    "type": "meta_tags_update",
                    "files_modified": ["src/pages/index.tsx"],
                    "description": "Updated meta tags for better SEO"
                }
            },
            {
                "task_type": "content_generation",
                "changes": {
                    "type": "content_update",
                    "files_modified": ["src/content/features.tsx"],
                    "description": "Updated feature descriptions"
                }
            },
            {
                "task_type": "error_fixing",
                "changes": {
                    "type": "bug_fix",
                    "files_modified": ["src/utils/api.ts"],
                    "description": "Fixed API error handling"
                }
            }
        ]

        # Process changes through each specialized agent
        for change in changes:
            print(f"\n🔄 Processing {change['task_type']}...")
            result = await system.process_task(change['task_type'], change)
            print(f"✅ {change['task_type']} completed: {result['status']}")

            # Notify CI/CD agent of task completion
            cicd_result = await system.process_task("cicd_deployment", {
                "task_type": change['task_type']
            })
            print(f"✅ CI/CD agent notified for {change['task_type']}")

        print("\n🔍 CI/CD agent will now:")
        print("1. Run old version (main branch) on port 3000")
        print("2. Run new version (sitesentry branch) on port 3001")
        print("3. Run auditor tool on both versions")
        print("4. Compare results and either:")
        print("   - Create a pull request if improvements are verified")
        print("   - Notify manager agent if further improvements needed")

        # Wait for deployment checks to complete
        print("\n⏳ Waiting for deployment checks...")
        await asyncio.sleep(5)  # Simulated wait for deployment checks

        print("\n✨ Full system test completed!")
        
    except Exception as e:
        print(f"\n❌ Error during system test: {str(e)}")
        raise

async def main():
    """Run the full system test."""
    # Ensure required environment variables are set
    required_env_vars = {
        "GOOGLE_API_KEY": "",
        "GITHUB_TOKEN": "",
        "GITHUB_OWNER": "metacatalysthq",
        "GITHUB_REPO": "landing-page",
        "WEBSITE_URL": "https://metacatalyst.in"
    }

    # Check and set environment variables
    for var, default_value in required_env_vars.items():
        if not os.getenv(var):
            os.environ[var] = default_value
            print(f"⚠️  Warning: {var} not set, using default value")

    print("\n🚀 Starting full system test...")
    await test_full_system()

if __name__ == "__main__":
    asyncio.run(main()) 