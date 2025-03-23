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
        self.completed_tasks: Dict[str, bool] = {
            "performance_monitoring": False,
            "seo_optimization": False,
            "content_generation": False,
            "error_fixing": False
        }
        self.github = GitHubController(
            token=system_config.api_keys.get('github_token', ''),
            repo_owner=system_config.github.repo_owner,
            repo_name=system_config.github.repo_name
        )
        self.server_processes = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("CI/CD Deployment Agent initialized")

    def _kill_process_on_port(self, port: int) -> None:
        """Kill a process running on a specific port.
        
        Args:
            port: Port number to check
        """
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        if platform.system() == 'Windows':
                            proc.terminate()  # Graceful termination
                        else:
                            proc.send_signal(signal.SIGTERM)
                        proc.wait(timeout=5)  # Wait for process to terminate
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

    async def run_local_server(self, port: int, branch: str) -> bool:
        """Run a local server for testing.
        
        Args:
            port: Port number to run the server on
            branch: Git branch to use
            
        Returns:
            bool: True if server started successfully
        """
        try:
            # Checkout the specified branch
            self.github.checkout_branch(branch)
            
            # Kill any existing process on the port
            self._kill_process_on_port(port)
            
            # Start the server (adjust command based on your project)
            process = subprocess.Popen(
                ["npm", "run", "dev", "--", f"--port={port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.system_config.workspace.path
            )
            
            # Store the process for cleanup
            self.server_processes[port] = process
            
            # Wait for server to start (adjust timeout as needed)
            await asyncio.sleep(10)
            
            # Check if server is running
            try:
                if platform.system() == 'Windows':
                    subprocess.check_output(["powershell", "-Command", f"Test-NetConnection -ComputerName localhost -Port {port}"])
                else:
                    subprocess.check_output(["curl", f"http://localhost:{port}"])
                return True
            except subprocess.CalledProcessError:
                return False
                
        except Exception as e:
            self.logger.error("Failed to start local server", error=str(e))
            return False

    async def run_auditor(self, url: str) -> Dict[str, Any]:
        """Run the auditor tool on a specific URL.
        
        Args:
            url: URL to audit
            
        Returns:
            Dict containing audit results
        """
        try:
            # Run lighthouse or your preferred auditing tool
            process = await asyncio.create_subprocess_exec(
                "lighthouse",
                url,
                "--output=json",
                "--quiet",
                "--chrome-flags='--headless'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Audit failed: {stderr.decode()}")
                
            # Parse and return audit results
            return {
                "performance": 0.0,  # Parse from stdout
                "accessibility": 0.0,
                "best_practices": 0.0,
                "seo": 0.0,
                "pwa": 0.0
            }
            
        except Exception as e:
            self.logger.error("Audit failed", error=str(e))
            return {}

    def compare_audit_results(self, old_results: Dict[str, Any], new_results: Dict[str, Any]) -> bool:
        """Compare audit results to determine if new version is better.
        
        Args:
            old_results: Audit results from old version
            new_results: Audit results from new version
            
        Returns:
            bool: True if new version is better
        """
        # Calculate weighted scores (adjust weights as needed)
        weights = {
            "performance": 0.4,
            "accessibility": 0.2,
            "best_practices": 0.2,
            "seo": 0.2
        }
        
        old_score = sum(old_results[key] * weights[key] for key in weights)
        new_score = sum(new_results[key] * weights[key] for key in weights)
        
        return new_score > old_score

    async def notify_task_completion(self, task_type: str) -> None:
        """Handle task completion notification from specialized agents.
        
        Args:
            task_type: Type of completed task
        """
        self.completed_tasks[task_type] = True
        
        # Check if all tasks are completed
        if all(self.completed_tasks.values()):
            await self.run_deployment_checks()

    async def run_deployment_checks(self) -> None:
        """Run deployment checks when all tasks are completed."""
        try:
            # Start old version (main branch)
            old_server_running = await self.run_local_server(3000, "main")
            if not old_server_running:
                raise Exception("Failed to start old version server")
            
            # Start new version (sitesentry branch)
            new_server_running = await self.run_local_server(3001, "sitesentry-test-branch")
            if not new_server_running:
                raise Exception("Failed to start new version server")
            
            # Run audits
            old_results = await self.run_auditor("http://localhost:3000")
            new_results = await self.run_auditor("http://localhost:3001")
            
            # Compare results
            is_better = self.compare_audit_results(old_results, new_results)
            
            if is_better:
                # Create pull request
                pr_result = self.github.create_pull_request(
                    title="AgentX: Automated improvements",
                    body=f"""
                    Automated improvements by AgentX

                    Audit Results Comparison:
                    Old Version:
                    {self._format_audit_results(old_results)}

                    New Version:
                    {self._format_audit_results(new_results)}
                    """,
                    base="main",
                    head="sitesentry-test-branch"
                )
                self.logger.info("Created pull request", pr_url=pr_result.get("url"))
            else:
                # Notify manager agent
                await self.notify_manager_agent(old_results, new_results)
                
        except Exception as e:
            self.logger.error("Deployment checks failed", error=str(e))
        finally:
            # Cleanup: Stop servers and reset branch
            self._cleanup_servers()

    def _format_audit_results(self, results: Dict[str, Any]) -> str:
        """Format audit results for PR description."""
        return "\n".join([
            f"- {key.title()}: {value * 100:.1f}%"
            for key, value in results.items()
        ])

    async def notify_manager_agent(self, old_results: Dict[str, Any], new_results: Dict[str, Any]) -> None:
        """Notify manager agent about required improvements.
        
        Args:
            old_results: Audit results from old version
            new_results: Audit results from new version
        """
        # Analyze differences
        improvements_needed = []
        for metric in old_results:
            if old_results[metric] > new_results[metric]:
                improvements_needed.append({
                    "metric": metric,
                    "old_score": old_results[metric],
                    "new_score": new_results[metric],
                    "difference": old_results[metric] - new_results[metric]
                })
        
        # Create detailed prompt
        prompt = f"""
        The new changes require improvements in the following areas:
        
        {self._format_improvements(improvements_needed)}
        
        Please analyze these metrics and suggest specific improvements to enhance the performance.
        """
        
        # Send to manager agent (implement this based on your system's architecture)
        # This should integrate with your existing manager agent communication method
        pass

    def _format_improvements(self, improvements: List[Dict[str, Any]]) -> str:
        """Format improvements needed for manager agent prompt."""
        return "\n".join([
            f"- {imp['metric'].title()}:\n"
            f"  - Old Score: {imp['old_score'] * 100:.1f}%\n"
            f"  - New Score: {imp['new_score'] * 100:.1f}%\n"
            f"  - Decrease: {imp['difference'] * 100:.1f}%"
            for imp in improvements
        ])

    def _cleanup_servers(self) -> None:
        """Stop local servers and reset Git branch."""
        try:
            # Stop server processes
            for port, process in self.server_processes.items():
                try:
                    if process.poll() is None:  # Process is still running
                        if platform.system() == 'Windows':
                            process.terminate()  # Graceful termination
                        else:
                            process.send_signal(signal.SIGTERM)
                        process.wait(timeout=5)
                except (subprocess.TimeoutExpired, Exception) as e:
                    self.logger.error(f"Failed to stop server on port {port}", error=str(e))
                    # Force kill if graceful termination fails
                    if process.poll() is None:
                        process.kill()

            # Kill any remaining processes on the ports
            self._kill_process_on_port(3000)
            self._kill_process_on_port(3001)
            
            # Reset Git branch
            self.github.checkout_branch("main")
            
            # Clear process dictionary
            self.server_processes.clear()
            
        except Exception as e:
            self.logger.error("Failed to cleanup servers", error=str(e))

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming task completion notifications.
        
        Args:
            data: Task data including task_type and completion status
            
        Returns:
            Processing results
        """
        try:
            task_type = data.get("task_type")
            if not task_type:
                raise ValueError("Task type not provided")
                
            if task_type not in self.completed_tasks:
                raise ValueError(f"Unknown task type: {task_type}")
                
            await self.notify_task_completion(task_type)
            
            return {
                "status": "success",
                "message": f"Task completion recorded for {task_type}"
            }
            
        except Exception as e:
            self.logger.error("Error processing task", error=str(e))
            return {
                "status": "error",
                "message": str(e)
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