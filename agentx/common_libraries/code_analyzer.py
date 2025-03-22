"""Code analysis utilities for performance monitoring."""

import os
from typing import Dict, Any, List
import subprocess
import ast
import structlog

logger = structlog.get_logger()

class CodeAnalyzer:
    """Analyzes code for performance issues and optimization opportunities."""

    def __init__(self):
        """Initialize the code analyzer."""
        self.logger = logger.bind(component="code_analyzer")

    def analyze_js_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze JavaScript file for performance issues.
        
        Args:
            filepath: Path to the JavaScript file
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            issues = []
            imports = []
            exports = []

            # Basic static analysis
            if 'document.write' in content:
                issues.append({
                    "type": "performance",
                    "message": "Use of document.write can block page rendering",
                    "severity": "warning"
                })

            if 'eval(' in content:
                issues.append({
                    "type": "security",
                    "message": "Use of eval is discouraged for security and performance reasons",
                    "severity": "warning"
                })

            # Check for large inline scripts
            if len(content) > 50000:  # 50KB
                issues.append({
                    "type": "performance",
                    "message": "Large JavaScript file may impact load time",
                    "severity": "warning"
                })

            # Extract imports
            import_lines = [line for line in content.split('\n') if 'import' in line or 'require(' in line]
            imports.extend(import_lines)

            # Extract exports
            export_lines = [line for line in content.split('\n') if 'export' in line]
            exports.extend(export_lines)

            return {
                "issues": issues,
                "imports": imports,
                "exports": exports,
                "size": len(content)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing JavaScript file: {str(e)}")
            return {"issues": [{"type": "error", "message": str(e)}]}

    def analyze_ts_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze TypeScript file for performance issues.
        
        Args:
            filepath: Path to the TypeScript file
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            issues = []
            imports = []
            exports = []

            # Run type checking if TypeScript is installed
            try:
                result = subprocess.run(['tsc', '--noEmit', filepath], 
                                     capture_output=True, 
                                     text=True)
                if result.returncode != 0:
                    issues.append({
                        "type": "typescript",
                        "message": result.stderr,
                        "severity": "error"
                    })
            except FileNotFoundError:
                self.logger.warning("TypeScript compiler not found, skipping type checking")

            # Basic static analysis
            if 'any' in content:
                issues.append({
                    "type": "typescript",
                    "message": "Use of 'any' type should be avoided",
                    "severity": "warning"
                })

            # Check file size
            if len(content) > 50000:  # 50KB
                issues.append({
                    "type": "performance",
                    "message": "Large TypeScript file may impact build time",
                    "severity": "warning"
                })

            # Extract imports
            import_lines = [line for line in content.split('\n') if 'import' in line]
            imports.extend(import_lines)

            # Extract exports
            export_lines = [line for line in content.split('\n') if 'export' in line]
            exports.extend(export_lines)

            return {
                "issues": issues,
                "imports": imports,
                "exports": exports,
                "size": len(content)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing TypeScript file: {str(e)}")
            return {"issues": [{"type": "error", "message": str(e)}]} 