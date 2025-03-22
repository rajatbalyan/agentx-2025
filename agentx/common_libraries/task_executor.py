"""Base task executor for specialized agents."""

from typing import Dict, Any, List, Optional
import structlog
from pathlib import Path
import ast
import re

logger = structlog.get_logger()

class TaskExecutor:
    """Base task executor for specialized agents."""
    
    def __init__(self):
        """Initialize the task executor."""
        self.logger = logger.bind(component="task_executor")
    
    def analyze_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task data to determine required actions.
        
        Args:
            task_data: Task data containing issues and requirements
            
        Returns:
            Analysis results with required actions
        """
        try:
            analysis = {
                "task_type": task_data.get("type", "unknown"),
                "priority": task_data.get("priority", "medium"),
                "score": task_data.get("score", 0),
                "issues": task_data.get("issues", []),
                "required_actions": [],
                "affected_files": [],
                "dependencies": []
            }
            
            # Extract required actions from issues
            for issue in analysis["issues"]:
                action = self._generate_action_from_issue(issue)
                if action:
                    analysis["required_actions"].append(action)
            
            # Identify affected files
            affected_files = self._identify_affected_files(task_data)
            if affected_files:
                analysis["affected_files"].extend(affected_files)
            
            # Identify dependencies
            dependencies = self._identify_dependencies(task_data)
            if dependencies:
                analysis["dependencies"].extend(dependencies)
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error analyzing task", error=str(e))
            raise
    
    def _generate_action_from_issue(self, issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a specific action from an issue."""
        try:
            return {
                "type": issue.get("type", "unknown"),
                "severity": issue.get("severity", "medium"),
                "description": issue.get("message", ""),
                "technical_details": issue.get("details", ""),
                "implementation_steps": self._break_down_implementation(issue)
            }
        except Exception as e:
            self.logger.error("Error generating action from issue", error=str(e))
            return None
    
    def _break_down_implementation(self, issue: Dict[str, Any]) -> List[str]:
        """Break down implementation into specific steps."""
        steps = []
        message = issue.get("message", "")
        details = issue.get("details", "")
        
        # Extract actionable items from message and details
        if message:
            steps.extend(self._extract_action_items(message))
        if details:
            steps.extend(self._extract_action_items(details))
        
        return steps
    
    def _extract_action_items(self, text: str) -> List[str]:
        """Extract actionable items from text."""
        items = []
        
        # Split by common action indicators
        indicators = ["should", "must", "needs to", "requires", "implement"]
        
        for indicator in indicators:
            if indicator in text.lower():
                # Extract the sentence containing the indicator
                sentences = text.split(". ")
                for sentence in sentences:
                    if indicator in sentence.lower():
                        items.append(sentence.strip())
        
        return items if items else [text]
    
    def _identify_affected_files(self, task_data: Dict[str, Any]) -> List[str]:
        """Identify files that need to be modified."""
        affected_files = []
        
        # Extract file paths from task data
        if "url" in task_data:
            # For website tasks, look for common web files
            affected_files.extend([
                "index.html",
                "styles.css",
                "main.js",
                "robots.txt",
                "sitemap.xml"
            ])
        
        return affected_files
    
    def _identify_dependencies(self, task_data: Dict[str, Any]) -> List[str]:
        """Identify required dependencies for the task."""
        dependencies = []
        
        # Extract dependencies based on task type and requirements
        task_type = task_data.get("type", "")
        
        if "performance" in task_type.lower():
            dependencies.extend([
                "webpack",
                "terser",
                "compression",
                "lazy-loading"
            ])
        elif "seo" in task_type.lower():
            dependencies.extend([
                "meta-tags",
                "structured-data",
                "xml-sitemap",
                "robots-txt"
            ])
        
        return dependencies
    
    def validate_changes(self, file_path: str, content: str) -> Dict[str, Any]:
        """Validate changes before applying them.
        
        Args:
            file_path: Path to the file being modified
            content: New content to validate
            
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check file extension
            ext = Path(file_path).suffix.lower()
            
            # Validate Python files
            if ext == '.py':
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    results["valid"] = False
                    results["errors"].append(f"Python syntax error: {str(e)}")
            
            # Validate HTML files
            elif ext == '.html':
                if not self._validate_html_structure(content):
                    results["valid"] = False
                    results["errors"].append("Invalid HTML structure")
            
            # Validate CSS files
            elif ext == '.css':
                if not self._validate_css_structure(content):
                    results["valid"] = False
                    results["errors"].append("Invalid CSS structure")
            
            # Validate JavaScript files
            elif ext == '.js':
                if not self._validate_js_structure(content):
                    results["valid"] = False
                    results["errors"].append("Invalid JavaScript structure")
            
            return results
            
        except Exception as e:
            self.logger.error("Error validating changes", error=str(e))
            results["valid"] = False
            results["errors"].append(str(e))
            return results
    
    def _validate_html_structure(self, content: str) -> bool:
        """Validate HTML structure."""
        # Basic HTML structure validation
        required_tags = ['<!DOCTYPE', '<html', '<head', '<body']
        return all(tag in content.lower() for tag in required_tags)
    
    def _validate_css_structure(self, content: str) -> bool:
        """Validate CSS structure."""
        # Basic CSS structure validation
        try:
            # Check for balanced braces
            return content.count('{') == content.count('}')
        except:
            return False
    
    def _validate_js_structure(self, content: str) -> bool:
        """Validate JavaScript structure."""
        # Basic JavaScript structure validation
        try:
            # Check for balanced braces and parentheses
            return (content.count('{') == content.count('}') and
                    content.count('(') == content.count(')'))
        except:
            return False 