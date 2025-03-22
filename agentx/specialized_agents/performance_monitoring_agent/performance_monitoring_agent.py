"""Performance monitoring agent for optimizing website performance."""

from typing import Dict, Any, List, Tuple, Optional
import os
import json
import subprocess
import structlog
from bs4 import BeautifulSoup
from agentx.common_libraries.base_agent import BaseAgent, AgentConfig
from agentx.common_libraries.system_config import SystemConfig
from agentx.common_libraries.code_analyzer import CodeAnalyzer

logger = structlog.get_logger()

class PerformanceMonitoringAgent(BaseAgent):
    """Agent responsible for monitoring and optimizing website performance."""
    
    # Framework-specific file patterns
    FRAMEWORK_PATTERNS = {
        "react": {
            "config_files": ["package.json", "tsconfig.json", "webpack.config.js", ".babelrc"],
            "source_files": [".jsx", ".tsx", ".js", ".ts"],
            "style_files": [".css", ".scss", ".sass", ".less", ".styled.js", ".styled.ts"],
            "build_files": ["dist", "build", ".next"]
        },
        "nextjs": {
            "config_files": ["next.config.js", "next.config.mjs", "tsconfig.json", "package.json"],
            "source_files": [".jsx", ".tsx", ".js", ".ts", ".mdx"],
            "style_files": [".css", ".scss", ".module.css", ".module.scss"],
            "build_files": [".next", "out"]
        },
        "vue": {
            "config_files": ["vue.config.js", "package.json", "tsconfig.json"],
            "source_files": [".vue", ".js", ".ts"],
            "style_files": [".css", ".scss", ".sass", ".less"],
            "build_files": ["dist"]
        },
        "angular": {
            "config_files": ["angular.json", "tsconfig.json", "package.json"],
            "source_files": [".ts", ".html", ".component.ts"],
            "style_files": [".css", ".scss", ".sass", ".less"],
            "build_files": ["dist"]
        },
        "raw": {
            "source_files": [".html", ".js", ".css"],
            "style_files": [".css"],
            "build_files": ["dist", "build"]
        }
    }
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig):
        """Initialize the performance monitoring agent.
        
        Args:
            config: Agent configuration
            system_config: System configuration
        """
        super().__init__(config, system_config)
        self.logger = logger.bind(agent="performance_monitoring_agent")
        self.modified_files = []
        self.scanned_files = []
        self.code_analyzer = CodeAnalyzer()
        self.detected_framework = None
        self.build_tool = None
        
    def track_file_modification(self, filepath: str, is_temp: bool = False) -> None:
        """Track a file that has been modified.
        
        Args:
            filepath: Path to the modified file
            is_temp: Whether this is a temporary file
        """
        self.modified_files.append({
            "path": filepath,
            "is_temporary": is_temp
        })
        self.logger.info("Tracked file modification", file=filepath, is_temp=is_temp)
        
    def track_file_scan(self, filepath: str) -> None:
        """Track a file that has been scanned for optimization.
        
        Args:
            filepath: Path to the scanned file
        """
        self.scanned_files.append(filepath)
        self.logger.info("Tracked file scan", file=filepath)
    
    def detect_framework(self, workspace_path: str) -> str:
        """Detect the web framework used in the project.
        
        Args:
            workspace_path: Path to the workspace
            
        Returns:
            Detected framework name or 'raw' if no framework detected
        """
        try:
            package_json_path = os.path.join(workspace_path, 'package.json')
            if os.path.exists(package_json_path):
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    
                    # Check for frameworks
                    if 'next' in dependencies:
                        return 'nextjs'
                    elif 'react' in dependencies and 'next' not in dependencies:
                        return 'react'
                    elif 'vue' in dependencies:
                        return 'vue'
                    elif '@angular/core' in dependencies:
                        return 'angular'
                        
            # Check for framework-specific files
            if os.path.exists(os.path.join(workspace_path, 'next.config.js')):
                return 'nextjs'
            elif os.path.exists(os.path.join(workspace_path, 'angular.json')):
                return 'angular'
            elif os.path.exists(os.path.join(workspace_path, 'vue.config.js')):
                return 'vue'
                
        except Exception as e:
            self.logger.error(f"Error detecting framework: {str(e)}")
            
        return 'raw'
    
    def detect_build_tool(self, workspace_path: str) -> Optional[str]:
        """Detect the build tool used in the project.
        
        Args:
            workspace_path: Path to the workspace
            
        Returns:
            Detected build tool name or None
        """
        try:
            package_json_path = os.path.join(workspace_path, 'package.json')
            if os.path.exists(package_json_path):
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    
                    if 'vite' in dependencies:
                        return 'vite'
                    elif 'webpack' in dependencies:
                        return 'webpack'
                    elif 'parcel' in dependencies:
                        return 'parcel'
                    elif '@angular-devkit/build-angular' in dependencies:
                        return 'angular-cli'
                        
            # Check for config files
            if os.path.exists(os.path.join(workspace_path, 'vite.config.js')):
                return 'vite'
            elif os.path.exists(os.path.join(workspace_path, 'webpack.config.js')):
                return 'webpack'
                
        except Exception as e:
            self.logger.error(f"Error detecting build tool: {str(e)}")
            
        return None
    
    def get_framework_specific_patterns(self) -> Dict[str, List[str]]:
        """Get file patterns specific to the detected framework."""
        if not self.detected_framework:
            return self.FRAMEWORK_PATTERNS["raw"]
        return self.FRAMEWORK_PATTERNS[self.detected_framework]
    
    def analyze_html_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze HTML file for performance issues.
        
        Args:
            filepath: Path to the HTML file
            
        Returns:
            Dictionary containing analysis results
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            
        results = {
            "render_blocking_resources": [],
            "unoptimized_images": [],
            "missing_resource_hints": True,
            "issues": []
        }
        
        # Check for render-blocking resources
        for script in soup.find_all('script'):
            if not script.get('defer') and not script.get('async'):
                results["render_blocking_resources"].append(script.get('src', 'inline-script'))
                
        # Check for unoptimized images
        for img in soup.find_all('img'):
            if not img.get('loading') == 'lazy':
                results["unoptimized_images"].append(img.get('src', 'unknown'))
                
        # Check for resource hints
        if not soup.find_all(['link'], rel=["preload", "prefetch", "preconnect"]):
            results["missing_resource_hints"] = True
            
        return results
    
    def analyze_javascript_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze JavaScript file for performance issues.
        
        Args:
            filepath: Path to the JavaScript file
            
        Returns:
            Dictionary containing analysis results
        """
        return self.code_analyzer.analyze_js_file(filepath)
    
    def analyze_typescript_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze TypeScript file for performance issues.
        
        Args:
            filepath: Path to the TypeScript file
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Run type checking
            result = subprocess.run(['tsc', '--noEmit', filepath], capture_output=True, text=True)
            issues = []
            
            if result.returncode != 0:
                issues.append({
                    "type": "typescript",
                    "message": result.stderr
                })
            
            # Use code analyzer for additional checks
            analyzer_results = self.code_analyzer.analyze_ts_file(filepath)
            if analyzer_results.get("issues"):
                issues.extend(analyzer_results["issues"])
            
            return {
                "issues": issues,
                "imports": analyzer_results.get("imports", []),
                "exports": analyzer_results.get("exports", [])
            }
        except Exception as e:
            self.logger.error(f"Error analyzing TypeScript file: {str(e)}")
            return {"issues": [{"type": "error", "message": str(e)}]}
    
    def analyze_framework_component(self, filepath: str) -> Dict[str, Any]:
        """Analyze framework-specific component files.
        
        Args:
            filepath: Path to the component file
            
        Returns:
            Dictionary containing analysis results
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext in ['.jsx', '.tsx']:
            # React/Next.js component analysis
            return self.analyze_react_component(filepath)
        elif ext == '.vue':
            # Vue component analysis
            return self.analyze_vue_component(filepath)
        elif '.component.ts' in filepath.lower():
            # Angular component analysis
            return self.analyze_angular_component(filepath)
        
        return {"issues": []}
    
    def validate_changes(self, modified_files: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """Validate changes made to files.
        
        Args:
            modified_files: List of modified file paths
            
        Returns:
            Tuple of (success, list of errors)
        """
        errors = []
        
        for file_info in modified_files:
            filepath = file_info["path"]
            if filepath.endswith('.js'):
                # Run ESLint
                try:
                    result = subprocess.run(['eslint', filepath], capture_output=True, text=True)
                    if result.returncode != 0:
                        errors.append(f"ESLint errors in {filepath}:\n{result.stdout}")
                except Exception as e:
                    errors.append(f"Error running ESLint on {filepath}: {str(e)}")
                    
            elif filepath.endswith('.css'):
                # Run stylelint
                try:
                    result = subprocess.run(['stylelint', filepath], capture_output=True, text=True)
                    if result.returncode != 0:
                        errors.append(f"Stylelint errors in {filepath}:\n{result.stdout}")
                except Exception as e:
                    errors.append(f"Error running Stylelint on {filepath}: {str(e)}")
                    
            elif filepath.endswith('.html'):
                # Run html-validator
                try:
                    result = subprocess.run(['html-validator', filepath], capture_output=True, text=True)
                    if result.returncode != 0:
                        errors.append(f"HTML validation errors in {filepath}:\n{result.stdout}")
                except Exception as e:
                    errors.append(f"Error validating HTML in {filepath}: {str(e)}")
        
        return len(errors) == 0, errors
    
    def identify_files_to_modify(self, workspace_path: str, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify files that need modification based on performance issues.
        
        Args:
            workspace_path: Path to the workspace
            issues: List of performance issues
            
        Returns:
            List of files to modify with their issues
        """
        self.detected_framework = self.detect_framework(workspace_path)
        self.build_tool = self.detect_build_tool(workspace_path)
        self.logger.info(f"Detected framework: {self.detected_framework}, build tool: {self.build_tool}")
        
        framework_patterns = self.get_framework_specific_patterns()
        files_to_modify = []
        
        for root, _, files in os.walk(workspace_path):
            for file in files:
                filepath = os.path.join(root, file)
                self.track_file_scan(filepath)
                ext = os.path.splitext(file)[1].lower()
                
                # Framework-specific source files
                if any(file.endswith(pattern) for pattern in framework_patterns["source_files"]):
                    if ext in ['.ts', '.tsx']:
                        analysis = self.analyze_typescript_file(filepath)
                    else:
                        analysis = self.analyze_framework_component(filepath)
                        
                    if analysis.get("issues"):
                        files_to_modify.append({
                            "path": filepath,
                            "type": "component",
                            "framework": self.detected_framework,
                            "issues": analysis
                        })
                
                # Style files
                elif any(file.endswith(pattern) for pattern in framework_patterns["style_files"]):
                    analysis = self.analyze_styles(filepath)
                    if analysis.get("issues"):
                        files_to_modify.append({
                            "path": filepath,
                            "type": "style",
                            "framework": self.detected_framework,
                            "issues": analysis
                        })
                
                # Images and other assets
                elif file.endswith(('.jpg', '.png', '.webp', '.svg')):
                    analysis = self.analyze_asset(filepath)
                    if analysis.get("needs_optimization"):
                        files_to_modify.append({
                            "path": filepath,
                            "type": "asset",
                            "issues": analysis
                        })
        
        return files_to_modify
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance optimization tasks.
        
        Args:
            input_data: Task data containing performance issues
            
        Returns:
            Processing results with optimization recommendations
        """
        try:
            self.logger.info("Processing performance task", task=input_data)
            
            task_data = input_data.get('data', {})
            metrics = task_data.get('metrics', {})
            issues = task_data.get('issues', [])
            workspace_path = task_data.get('workspace', {}).get('path')
            
            if not workspace_path:
                return {
                    "status": "error",
                    "error": "No workspace path provided"
                }
            
            # Identify files that need modification
            files_to_modify = self.identify_files_to_modify(workspace_path, issues)
            
            # Generate recommendations based on file analysis
            recommendations = []
            for file_info in files_to_modify:
                if file_info["type"] == "html":
                    if file_info["issues"]["render_blocking_resources"]:
                        recommendations.append({
                            "file": file_info["path"],
                            "issue": "Render-blocking resources",
                            "recommendations": [
                                "Add defer/async to scripts",
                                "Move CSS to end of body",
                                "Implement resource hints"
                            ]
                        })
                elif file_info["type"] == "javascript":
                    recommendations.append({
                        "file": file_info["path"],
                        "issue": "JavaScript optimization needed",
                        "recommendations": [
                            "Implement code splitting",
                            "Remove unused code",
                            "Optimize bundle size"
                        ]
                    })
            
            # Track files for modification
            for file_info in files_to_modify:
                self.track_file_modification(file_info["path"])
            
            # Validate any changes made
            if self.modified_files:
                is_valid, validation_errors = self.validate_changes(self.modified_files)
                if not is_valid:
                    return {
                        "status": "error",
                        "error": "Validation failed",
                        "validation_errors": validation_errors
                    }
            
            return {
                "status": "success",
                "action_plan": {
                    "priority": task_data.get('priority', 'medium'),
                    "current_score": task_data.get('score', 0),
                    "target_score": 90,
                    "files_to_modify": files_to_modify,
                    "recommendations": recommendations,
                    "implementation_steps": self._generate_implementation_steps(),
                    "files": {
                        "modified": self.modified_files,
                        "scanned": self.scanned_files
                    }
                },
                "validation_status": "passed"
            }
            
        except Exception as e:
            self.logger.error("Error processing performance task", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        pass 