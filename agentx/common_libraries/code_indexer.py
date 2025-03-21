"""Code indexing and understanding system for AgentX."""

import os
from typing import Dict, List, Optional, Set, Tuple, Any
import ast
from pathlib import Path
import structlog
from dataclasses import dataclass
from chromadb import Collection
import networkx as nx
import re

from agentx.common_libraries.db_manager import db_manager

logger = structlog.get_logger()

@dataclass
class CodeEntity:
    """Represents a code entity (function, class, variable, etc.)."""
    name: str
    type: str  # 'function', 'class', 'variable', etc.
    file_path: str
    start_line: int
    end_line: int
    docstring: Optional[str]
    dependencies: Set[str]
    code_snippet: str
    complexity: Optional[int] = None
    security_issues: Optional[List[str]] = None
    test_coverage: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class CodeIndexer:
    """Indexes and provides understanding of codebases."""

    # High-risk patterns that need careful review
    SECURITY_PATTERNS = {
        'sql_injection': r'execute\s*\(\s*[\'"][^\']*%.*[\'"]\s*%',
        'shell_injection': r'os\.system\(|subprocess\.call\(|eval\(|exec\(',
        'path_traversal': r'\.\./',
        'hardcoded_secrets': r'password\s*=\s*[\'"][^\'"]+[\'"]\s*$|api_key\s*=\s*[\'"][^\'"]+[\'"]\s*$',
        'unsafe_deserialization': r'pickle\.loads\(|yaml\.load\(',
        # Additional security patterns
        'xss_vulnerability': r'render_template\s*\(.*\+\s*.*\)|response\.write\s*\(.*\+\s*.*\)',
        'open_redirect': r'redirect\s*\(\s*request\.args\.get\s*\(',
        'file_access': r'open\s*\(\s*.*\+\s*.*\)',
        'command_injection': r'subprocess\.Popen\(.*shell\s*=\s*True\)',
        'jwt_none_algorithm': r'jwt\.decode\(.*verify\s*=\s*False\)',
        'weak_crypto': r'md5\(|sha1\('
    }

    # Patterns indicating potential code smells
    CODE_SMELL_PATTERNS = {
        'long_method': 15,  # lines threshold
        'too_many_parameters': 5,  # parameters threshold
        'complex_condition': r'if.*and.*and.*or|if.*or.*or.*and',
        'nested_loops': r'for.*for|while.*while',
        # Additional code smells
        'global_state': r'global\s+[a-zA-Z_][a-zA-Z0-9_]*',
        'magic_numbers': r'\b(?<!\.)\d{4,}\b(?!\.)',
        'catch_all_except': r'except\s*:',
        'mutable_defaults': r'def\s+\w+\s*\([^)]*=\s*(\[\s*\]|\{\s*\}|\(\s*\))',
        'long_parameter_list': r'def\s+\w+\s*\([^)]{80,}\)',
        'boolean_flag': r'def\s+\w+\s*\([^)]*\bbool\b[^)]*\)'
    }

    # Performance patterns to analyze
    PERFORMANCE_PATTERNS = {
        'inefficient_list_operation': r'for\s+\w+\s+in\s+range\(len\(',
        'expensive_operation_in_loop': r'for.*:.*\.(sort|reverse|copy)\(\)',
        'quadratic_operation': r'for.*:\s*for\s+\w+\s+in\s+range\(',
        'memory_intensive': r'\.append\(.*\).*for.*in',
        'cpu_intensive': r'recursive_.*\(|factorial.*\(',
        'network_call_in_loop': r'for.*:\s*(requests\.|urllib\.|http\.)',
        'db_query_in_loop': r'for.*:\s*(execute|query|find)\(',
        'large_memory_allocation': r'numpy\.zeros\(.*\d{5,}.*\)|torch\.zeros\(.*\d{5,}.*\)'
    }

    def __init__(self, workspace_path: str, db_path: str = "data/memory/code_index"):
        """Initialize the code indexer.
        
        Args:
            workspace_path: Root path of the codebase
            db_path: Path to store the vector database
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB for semantic search using the global database manager
        self.chroma_client = db_manager.initialize(
            os.path.join(self.db_path.parent, "chroma")
        )
        
        # Create or get collections
        self.code_collection = self.chroma_client.get_or_create_collection(
            name="code_entities",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize dependency graph
        self.dependency_graph = nx.DiGraph()
        
        self.logger = logger.bind(component="code_indexer")

    async def analyze_security(self, entity: CodeEntity) -> List[str]:
        """Analyze code entity for security issues.
        
        Args:
            entity: Code entity to analyze
            
        Returns:
            List of identified security issues
        """
        issues = []
        for issue_type, pattern in self.SECURITY_PATTERNS.items():
            if re.search(pattern, entity.code_snippet, re.IGNORECASE):
                issues.append(f"Potential {issue_type} vulnerability detected")
        return issues

    async def analyze_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of code.
        
        Args:
            node: AST node to analyze
            
        Returns:
            Complexity score
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers)
        
        return complexity

    async def analyze_code_smells(self, entity: CodeEntity, node: ast.AST) -> List[str]:
        """Analyze code for potential code smells.
        
        Args:
            entity: Code entity to analyze
            node: AST node of the entity
            
        Returns:
            List of identified code smells
        """
        smells = []
        
        # Check method length
        if len(entity.code_snippet.splitlines()) > self.CODE_SMELL_PATTERNS['long_method']:
            smells.append("Method is too long")
        
        # Check parameter count for functions
        if isinstance(node, ast.FunctionDef):
            if len(node.args.args) > self.CODE_SMELL_PATTERNS['too_many_parameters']:
                smells.append("Too many parameters")
        
        # Check complex conditions and nested loops
        for smell_type in ['complex_condition', 'nested_loops']:
            if re.search(self.CODE_SMELL_PATTERNS[smell_type], entity.code_snippet):
                smells.append(f"Contains {smell_type.replace('_', ' ')}")
        
        return smells

    async def analyze_dependencies_risk(self, entity_name: str) -> Dict[str, Any]:
        """Analyze risks in dependency relationships.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Risk analysis results
        """
        deps = await self.get_dependencies(entity_name)
        
        # Calculate various risk metrics
        circular_deps = list(nx.simple_cycles(self.dependency_graph))
        is_in_circular = any(entity_name in cycle for cycle in circular_deps)
        
        # Calculate dependency depth
        try:
            max_depth = max(len(path) for path in nx.all_simple_paths(
                self.dependency_graph,
                entity_name,
                list(deps["outgoing"])
            )) if deps["outgoing"] else 0
        except nx.NetworkXNoPath:
            max_depth = 0
        
        return {
            "circular_dependencies": is_in_circular,
            "dependency_depth": max_depth,
            "direct_dependencies": len(deps["outgoing"]),
            "dependent_modules": len(deps["incoming"]),
            "risk_score": self._calculate_dependency_risk_score(
                is_in_circular,
                max_depth,
                len(deps["outgoing"]),
                len(deps["incoming"])
            )
        }

    def _calculate_dependency_risk_score(
        self,
        has_circular: bool,
        depth: int,
        direct_deps: int,
        dependents: int
    ) -> float:
        """Calculate a risk score based on dependency metrics.
        
        Args:
            has_circular: Whether circular dependencies exist
            depth: Maximum dependency depth
            direct_deps: Number of direct dependencies
            dependents: Number of dependent modules
            
        Returns:
            Risk score between 0 and 1
        """
        score = 0.0
        
        # Circular dependencies are very risky
        if has_circular:
            score += 0.4
        
        # Deep dependency chains are risky
        score += min(0.3, depth * 0.1)
        
        # Many direct dependencies increase risk
        score += min(0.15, direct_deps * 0.03)
        
        # Many dependents increase risk
        score += min(0.15, dependents * 0.03)
        
        return min(1.0, score)

    async def analyze_performance(self, entity: CodeEntity, node: ast.AST) -> Dict[str, Any]:
        """Analyze code for performance issues.
        
        Args:
            entity: Code entity to analyze
            node: AST node of the entity
            
        Returns:
            Dictionary of performance metrics and issues
        """
        issues = []
        metrics = {
            "time_complexity": "O(1)",  # Default
            "space_complexity": "O(1)",  # Default
            "performance_score": 1.0,    # Default (1.0 = best, 0.0 = worst)
            "bottlenecks": []
        }
        
        # Check for performance patterns
        for issue_type, pattern in self.PERFORMANCE_PATTERNS.items():
            if re.search(pattern, entity.code_snippet, re.IGNORECASE):
                issues.append(issue_type)
                metrics["performance_score"] -= 0.1  # Decrease score for each issue
        
        # Analyze time complexity
        metrics["time_complexity"] = self._analyze_time_complexity(node)
        
        # Analyze space complexity
        metrics["space_complexity"] = self._analyze_space_complexity(node)
        
        # Identify bottlenecks
        metrics["bottlenecks"] = self._identify_bottlenecks(entity, issues)
        
        # Adjust performance score based on complexities
        complexity_penalty = self._calculate_complexity_penalty(
            metrics["time_complexity"],
            metrics["space_complexity"]
        )
        metrics["performance_score"] = max(0.1, metrics["performance_score"] - complexity_penalty)
        
        return metrics

    def _analyze_time_complexity(self, node: ast.AST) -> str:
        """Analyze time complexity of code.
        
        Args:
            node: AST node to analyze
            
        Returns:
            Estimated time complexity
        """
        nested_loops = 0
        has_recursion = False
        
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)):
                nested_loops += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == node.name if isinstance(node, ast.FunctionDef) else False:
                        has_recursion = True
        
        if has_recursion:
            return "O(2^n)"  # Assume exponential for recursive functions
        elif nested_loops > 1:
            return f"O(n^{nested_loops})"
        elif nested_loops == 1:
            return "O(n)"
        else:
            return "O(1)"

    def _analyze_space_complexity(self, node: ast.AST) -> str:
        """Analyze space complexity of code.
        
        Args:
            node: AST node to analyze
            
        Returns:
            Estimated space complexity
        """
        array_allocations = 0
        has_recursion = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.List) or isinstance(child, ast.Dict):
                array_allocations += 1
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    if child.func.id == node.name if isinstance(node, ast.FunctionDef) else False:
                        has_recursion = True
        
        if has_recursion:
            return "O(n)"  # Assume linear space for recursion
        elif array_allocations > 0:
            return "O(n)"
        else:
            return "O(1)"

    def _identify_bottlenecks(
        self,
        entity: CodeEntity,
        performance_issues: List[str]
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks in code.
        
        Args:
            entity: Code entity to analyze
            performance_issues: List of identified performance issues
            
        Returns:
            List of bottlenecks with details
        """
        bottlenecks = []
        
        for issue in performance_issues:
            bottleneck = {
                "type": issue,
                "severity": "high" if "quadratic" in issue or "cpu_intensive" in issue else "medium",
                "suggestion": self._get_performance_suggestion(issue)
            }
            bottlenecks.append(bottleneck)
        
        return bottlenecks

    def _get_performance_suggestion(self, issue_type: str) -> str:
        """Get suggestion for fixing performance issue.
        
        Args:
            issue_type: Type of performance issue
            
        Returns:
            Suggestion for improvement
        """
        suggestions = {
            "inefficient_list_operation": "Use enumerate() instead of range(len())",
            "expensive_operation_in_loop": "Move operation outside loop if possible",
            "quadratic_operation": "Consider using more efficient data structure or algorithm",
            "memory_intensive": "Use generators or itertools for memory efficiency",
            "cpu_intensive": "Consider caching results or using dynamic programming",
            "network_call_in_loop": "Use async/await or batch requests",
            "db_query_in_loop": "Use batch queries or JOIN operations",
            "large_memory_allocation": "Consider using sparse arrays or chunking"
        }
        return suggestions.get(issue_type, "Review and optimize the code")

    def _calculate_complexity_penalty(self, time_complexity: str, space_complexity: str) -> float:
        """Calculate performance penalty based on complexities.
        
        Args:
            time_complexity: Time complexity string
            space_complexity: Space complexity string
            
        Returns:
            Penalty score between 0 and 1
        """
        # Map complexity to penalty
        complexity_penalties = {
            "O(1)": 0.0,
            "O(log n)": 0.1,
            "O(n)": 0.2,
            "O(n log n)": 0.3,
            "O(n^2)": 0.4,
            "O(n^3)": 0.6,
            "O(2^n)": 0.8
        }
        
        time_penalty = complexity_penalties.get(time_complexity, 0.5)
        space_penalty = complexity_penalties.get(space_complexity, 0.3)
        
        return (time_penalty + space_penalty) / 2

    async def _index_file(self, file_path: Path) -> None:
        """Index a single file.
        
        Args:
            file_path: Path to the file to index
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Extract code entities
            entities = []
            for node in ast.walk(tree):
                entity = None
                
                if isinstance(node, ast.FunctionDef):
                    entity = CodeEntity(
                        name=node.name,
                        type='function',
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        docstring=ast.get_docstring(node),
                        dependencies=self._extract_dependencies(node),
                        code_snippet=content[node.lineno-1:node.end_lineno]
                    )
                    # Add complexity analysis
                    entity.complexity = await self.analyze_complexity(node)
                    # Add security analysis
                    entity.security_issues = await self.analyze_security(entity)
                    # Add performance analysis
                    entity.performance_metrics = await self.analyze_performance(entity, node)
                    
                elif isinstance(node, ast.ClassDef):
                    entity = CodeEntity(
                        name=node.name,
                        type='class',
                        file_path=str(file_path),
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        docstring=ast.get_docstring(node),
                        dependencies=self._extract_dependencies(node),
                        code_snippet=content[node.lineno-1:node.end_lineno]
                    )
                    # Add complexity analysis for class methods
                    total_complexity = 0
                    method_count = 0
                    total_performance_score = 0.0
                    
                    for method in [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]:
                        total_complexity += await self.analyze_complexity(method)
                        method_count += 1
                        # Analyze performance for each method
                        perf_metrics = await self.analyze_performance(entity, method)
                        total_performance_score += perf_metrics["performance_score"]
                    
                    entity.complexity = total_complexity / max(1, method_count)
                    # Add security analysis
                    entity.security_issues = await self.analyze_security(entity)
                    # Add average performance metrics
                    entity.performance_metrics = {
                        "performance_score": total_performance_score / max(1, method_count)
                    }
                
                if entity:
                    entities.append(entity)
                    # Add to dependency graph
                    self.dependency_graph.add_node(entity.name)
                    for dep in entity.dependencies:
                        self.dependency_graph.add_edge(entity.name, dep)
            
            # Add to vector database
            self._add_to_vector_db(entities)
            
        except Exception as e:
            self.logger.error("Error indexing file", file=str(file_path), error=str(e))

    def _extract_dependencies(self, node: ast.AST) -> Set[str]:
        """Extract dependencies from an AST node.
        
        Args:
            node: AST node to analyze
            
        Returns:
            Set of dependency names
        """
        dependencies = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                dependencies.add(child.id)
            elif isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    dependencies.add(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    dependencies.add(child.func.attr)
        
        return dependencies

    def _add_to_vector_db(self, entities: List[CodeEntity]) -> None:
        """Add code entities to the vector database.
        
        Args:
            entities: List of code entities to add
        """
        if not entities:
            return
            
        documents = []
        metadatas = []
        ids = []
        
        for i, entity in enumerate(entities):
            # Create searchable document
            doc = f"{entity.name} {entity.type}\n"
            if entity.docstring:
                doc += f"{entity.docstring}\n"
            doc += entity.code_snippet
            
            documents.append(doc)
            metadatas.append({
                "name": entity.name,
                "type": entity.type,
                "file_path": entity.file_path,
                "start_line": entity.start_line,
                "end_line": entity.end_line
            })
            # Add a unique identifier to prevent duplicates
            ids.append(f"{entity.file_path}:{entity.name}:{i}")
        
        try:
            self.code_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        except Exception as e:
            self.logger.error(
                "Error adding to vector database",
                error=str(e),
                num_entities=len(entities)
            )
            # Try adding one by one to identify problematic entries
            for i, (doc, meta, id_) in enumerate(zip(documents, metadatas, ids)):
                try:
                    self.code_collection.add(
                        documents=[doc],
                        metadatas=[meta],
                        ids=[id_]
                    )
                except Exception as e:
                    self.logger.error(
                        "Error adding single entity",
                        error=str(e),
                        entity_id=id_,
                        file_path=meta["file_path"]
                    )

    async def find_relevant_code(self, query: str, limit: int = 5) -> List[CodeEntity]:
        """Find code entities relevant to a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant code entities
        """
        results = self.code_collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        entities = []
        for i, metadata in enumerate(results['metadatas'][0]):
            with open(metadata['file_path'], 'r', encoding='utf-8') as f:
                content = f.read().splitlines()
            
            code_snippet = "\n".join(
                content[metadata['start_line']-1:metadata['end_line']]
            )
            
            entities.append(CodeEntity(
                name=metadata['name'],
                type=metadata['type'],
                file_path=metadata['file_path'],
                start_line=metadata['start_line'],
                end_line=metadata['end_line'],
                docstring=None,  # We don't store this in metadata
                dependencies=set(),  # We don't store this in metadata
                code_snippet=code_snippet
            ))
        
        return entities

    async def get_dependencies(self, entity_name: str) -> Dict[str, List[str]]:
        """Get dependencies for a code entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Dictionary with incoming and outgoing dependencies
        """
        if entity_name not in self.dependency_graph:
            return {"incoming": [], "outgoing": []}
            
        return {
            "incoming": list(self.dependency_graph.predecessors(entity_name)),
            "outgoing": list(self.dependency_graph.successors(entity_name))
        }

    async def suggest_modification_points(self, task_description: str) -> List[Dict[str, any]]:
        """Suggest points in the code where modifications might be needed.
        
        Args:
            task_description: Description of the task
            
        Returns:
            List of suggested modification points
        """
        # Find relevant code entities
        relevant_entities = await self.find_relevant_code(task_description)
        
        suggestions = []
        for entity in relevant_entities:
            # Get dependencies and risks
            deps = await self.get_dependencies(entity.name)
            dep_risks = await self.analyze_dependencies_risk(entity.name)
            
            # Get code smells
            tree = ast.parse(entity.code_snippet)
            code_smells = await self.analyze_code_smells(
                entity,
                next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
            )
            
            # Calculate comprehensive risk score
            risk_score = dep_risks["risk_score"]
            if entity.security_issues:
                risk_score += 0.3
            risk_score += len(code_smells) * 0.1
            risk_score = min(1.0, risk_score)
            
            # Calculate impact score based on dependencies and complexity
            impact_score = (
                len(deps["incoming"]) +
                len(deps["outgoing"]) +
                (entity.complexity or 0) / 10
            )
            
            suggestions.append({
                "entity": entity,
                "dependencies": deps,
                "impact_score": impact_score,
                "risk_score": risk_score,
                "security_issues": entity.security_issues,
                "code_smells": code_smells,
                "dependency_risks": dep_risks,
                "confidence": self._calculate_confidence(
                    entity,
                    impact_score,
                    risk_score
                ),
                "modification_type": self._suggest_modification_type(
                    task_description,
                    entity
                ),
                "safety_checks": self._generate_safety_checks(
                    entity,
                    deps,
                    code_smells,
                    entity.security_issues
                )
            })
        
        # Sort by confidence and impact score
        suggestions.sort(
            key=lambda x: (x["confidence"], -x["risk_score"]),
            reverse=True
        )
        
        return suggestions

    def _calculate_confidence(
        self,
        entity: CodeEntity,
        impact_score: float,
        risk_score: float
    ) -> float:
        """Calculate confidence score for a suggestion.
        
        Args:
            entity: Code entity
            impact_score: Impact score
            risk_score: Risk score
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Good documentation increases confidence
        if entity.docstring:
            confidence += 0.2
        
        # High impact decreases confidence
        confidence -= min(0.3, impact_score * 0.05)
        
        # High risk decreases confidence
        confidence -= risk_score * 0.3
        
        # Low complexity increases confidence
        if entity.complexity:
            confidence += max(0, 0.2 - (entity.complexity * 0.02))
        
        return max(0.1, min(1.0, confidence))

    def _generate_safety_checks(
        self,
        entity: CodeEntity,
        deps: Dict[str, List[str]],
        code_smells: List[str],
        security_issues: Optional[List[str]]
    ) -> List[str]:
        """Generate list of safety checks for modification.
        
        Args:
            entity: Code entity
            deps: Dependencies
            code_smells: Identified code smells
            security_issues: Identified security issues
            
        Returns:
            List of safety checks
        """
        checks = []
        
        # Basic checks
        checks.append("Create backup of affected files")
        checks.append("Create new feature branch")
        
        # Dependency-based checks
        if deps["incoming"]:
            checks.append("Test all dependent modules")
            checks.append("Verify interface compatibility")
        
        # Security-based checks
        if security_issues:
            checks.extend([
                f"Address security issue: {issue}"
                for issue in security_issues
            ])
        
        # Code smell checks
        if code_smells:
            checks.extend([
                f"Consider refactoring: {smell}"
                for smell in code_smells
            ])
        
        # Complexity checks
        if entity.complexity and entity.complexity > 10:
            checks.append("Consider breaking down complex logic")
            checks.append("Add detailed inline documentation")
        
        # Testing checks
        checks.extend([
            "Add/update unit tests",
            "Add/update integration tests",
            "Verify error handling",
            "Check edge cases"
        ])
        
        return checks

    def _suggest_modification_type(
        self,
        task_description: str,
        entity: CodeEntity
    ) -> str:
        """Suggest the type of modification needed.
        
        Args:
            task_description: Description of the task
            entity: Code entity to analyze
            
        Returns:
            Suggested modification type
        """
        # Simple heuristic-based suggestion
        if "bug" in task_description.lower():
            return "fix"
        elif "feature" in task_description.lower():
            return "add"
        elif "refactor" in task_description.lower():
            return "modify"
        else:
            return "analyze"

    async def index_codebase(self) -> None:
        """Index the entire codebase.
        
        This method walks through all Python files in the workspace and indexes them.
        """
        self.logger.info("Starting codebase indexing", workspace_path=str(self.workspace_path))
        
        # Define directories and files to ignore
        ignore_patterns = {
            'node_modules',
            'venv',
            'env',
            '__pycache__',
            '.git',
            '.pytest_cache',
            'dist',
            'build',
            '.vscode',
            '.idea'
        }
        
        try:
            # Walk through all Python files in the workspace
            for root, dirs, files in os.walk(self.workspace_path):
                # Remove ignored directories from dirs list (modifying in place)
                dirs[:] = [d for d in dirs if d not in ignore_patterns]
                
                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        try:
                            await self._index_file(file_path)
                        except Exception as e:
                            self.logger.error(
                                "Error indexing file",
                                file_path=str(file_path),
                                error=str(e)
                            )
                            continue
            
            self.logger.info("Codebase indexing completed")
            
        except Exception as e:
            self.logger.error("Error during codebase indexing", error=str(e))
            raise 