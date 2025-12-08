"""
Distributed Code Indexer
Creates separate index files for each directory with references to subdirectories and code files.
"""

import os
import ast
import json
import hashlib
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from src.distributed_models import (
    CodeLanguage, CodeElementType, CodeElementMetadata,
    FileMetadata, SubdirectoryReference, DirectoryIndex, RepositoryIndex
)


class DistributedCodeIndexer:
    """
    Creates distributed index structure with separate files per directory.
    
    Structure:
    - repo_index.json: Root repository index
    - .index/: Directory containing all index files
      - root_index.json: Root directory index
      - src_index.json: src/ directory index
      - src_openai_index.json: src/openai/ directory index
      - etc.
    """
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o-mini", max_workers: int = 10):
        """Initialize indexer with OpenAI client."""
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.indexed_dirs = {}  # Cache for indexed directories
        self.max_workers = max_workers  # Parallel workers for LLM calls
        self.summary_cache = {}  # Cache for file summaries (hash -> summary)
    
    def index_repository(
        self,
        repo_path: str,
        output_dir: str,
        generate_summaries: bool = True
    ) -> RepositoryIndex:
        """
        Index a repository with distributed index files.
        
        Args:
            repo_path: Path to repository root
            output_dir: Directory to store index files
            generate_summaries: Whether to generate LLM summaries
            
        Returns:
            RepositoryIndex with reference to root directory index
        """
        print(f"\n{'='*80}")
        print(f"DISTRIBUTED CODE INDEXER")
        print(f"{'='*80}")
        print(f"Repository: {repo_path}")
        print(f"Output: {output_dir}")
        print(f"Summaries: {generate_summaries}")
        print(f"{'='*80}\n")
        
        # Create output directory (hierarchical structure)
        os.makedirs(output_dir, exist_ok=True)
        
        # Index root directory (recursive, bottom-up)
        # This will create a hierarchical folder structure mirroring the repo
        root_index = self._index_directory(
            dir_path=repo_path,
            repo_root=repo_path,
            output_root=output_dir,
            parent_index_path=None,
            generate_summaries=generate_summaries
        )
        
        # Create repository index
        repo_name = os.path.basename(repo_path)
        repo_index = RepositoryIndex(
            repo_id=self._generate_id(repo_path),
            name=repo_name,
            repo_path=repo_path,
            index_root_path=output_dir,
            root_index_path=root_index.index_file_path,
            primary_language="python"
        )
        
        # Calculate statistics (bottom-up from root)
        self._calculate_statistics(repo_index, root_index, output_dir)
        
        # Generate repository summary
        if generate_summaries:
            repo_index.summary = self._generate_repo_summary(repo_index, root_index)
            repo_index.architecture_description = f"Distributed index with {repo_index.total_directories} directories"
        
        # Save repository index
        repo_index_path = os.path.join(output_dir, "repo_index.json")
        with open(repo_index_path, 'w') as f:
            json.dump(repo_index.model_dump(), f, indent=2, default=str)
        
        print(f"\n{'='*80}")
        print(f"INDEXING COMPLETE")
        print(f"{'='*80}")
        print(f"Repository index: {repo_index_path}")
        print(f"Directory indices: {index_dir}/")
        print(f"Total files: {repo_index.total_files}")
        print(f"Total directories: {repo_index.total_directories}")
        print(f"Total lines: {repo_index.total_lines:,}")
        print(f"{'='*80}\n")
        
        return repo_index
    
    def _index_directory(
        self,
        dir_path: str,
        repo_root: str,
        output_root: str,
        parent_index_path: Optional[str],
        generate_summaries: bool
    ) -> DirectoryIndex:
        """
        Index a directory recursively (bottom-up) and save to hierarchical file.
        
        Creates a folder structure that mirrors the code repository.
        Each directory gets its own index.json file in the corresponding location.
        
        Returns DirectoryIndex with references to subdirectory indices.
        """
        relative_path = os.path.relpath(dir_path, repo_root)
        print(f"\n📁 Indexing directory: {relative_path}")
        
        # Create hierarchical index directory path
        if relative_path == '.':
            index_dir_path = output_root
        else:
            index_dir_path = os.path.join(output_root, relative_path)
        
        os.makedirs(index_dir_path, exist_ok=True)
        
        # Index file is always named "index.json" in its directory
        index_file_path = os.path.join(index_dir_path, "index.json")
        
        # Create directory index
        dir_index = DirectoryIndex(
            dir_path=dir_path,
            relative_path=relative_path,
            index_file_path=index_file_path,
            parent_index_path=parent_index_path
        )
        
        try:
            items = sorted(os.listdir(dir_path))
        except PermissionError:
            return dir_index
        
        # First, index all files in this directory
        for item in items:
            item_path = os.path.join(dir_path, item)
            
            # Skip hidden files and common ignore patterns
            if item.startswith('.') or item in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']:
                continue
            
            if os.path.isfile(item_path) and item.endswith('.py'):
                file_metadata = self._index_python_file(item_path, repo_root, generate_summaries)
                if file_metadata:
                    dir_index.files.append(file_metadata)
                    dir_index.direct_file_count += 1
                    print(f"  ✓ Indexed: {os.path.relpath(item_path, repo_root)} ({len(file_metadata.elements)} elements)")
        
        # Second, recursively index subdirectories (BOTTOM-UP)
        for item in items:
            item_path = os.path.join(dir_path, item)
            
            if item.startswith('.') or item in ['node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build']:
                continue
            
            if os.path.isdir(item_path):
                # BOTTOM-UP: Recursively index subdirectory first (leaf to root)
                # This ensures child summaries are available when generating parent summary
                subdir_index = self._index_directory(
                    dir_path=item_path,
                    repo_root=repo_root,
                    output_root=output_root,
                    parent_index_path=index_file_path,
                    generate_summaries=generate_summaries
                )
                
                # Create reference to subdirectory
                subdir_ref = SubdirectoryReference(
                    dir_name=item,
                    dir_path=item_path,
                    relative_path=subdir_index.relative_path,
                    index_file_path=subdir_index.index_file_path,
                    summary=subdir_index.summary,
                    file_count=subdir_index.total_file_count,
                    subdir_count=len(subdir_index.subdirectories)
                )
                
                dir_index.subdirectories.append(subdir_ref)
        
        # Calculate statistics for this directory (bottom-up aggregation)
        dir_index.total_file_count = dir_index.direct_file_count
        dir_index.total_lines = sum(f.total_lines for f in dir_index.files)
        
        # Add subdirectory statistics (already calculated bottom-up)
        for subdir_ref in dir_index.subdirectories:
            dir_index.total_file_count += subdir_ref.file_count
        
        # BATCH GENERATE: Generate file summaries in parallel for this directory
        if generate_summaries and dir_index.files:
            self._batch_generate_file_summaries(dir_index.files)
        
        # BOTTOM-UP: Generate directory summary AFTER all children are indexed
        # This ensures we have complete information from all subdirectories
        if generate_summaries and (dir_index.files or dir_index.subdirectories):
            print(f"  🤖 Generating summary for {relative_path}...")
            dir_index.summary = self._generate_directory_summary(dir_index)
        
        # Save this directory's index to hierarchical location
        with open(index_file_path, 'w') as f:
            json.dump(dir_index.model_dump(), f, indent=2, default=str)
        
        print(f"  ✅ Saved: {os.path.relpath(index_file_path, output_root)}")
        print(f"     Files: {dir_index.direct_file_count} direct, {dir_index.total_file_count} total")
        print(f"     Subdirs: {len(dir_index.subdirectories)}")
        
        return dir_index
    
    def _index_python_file(
        self,
        file_path: str,
        repo_root: str,
        generate_summaries: bool
    ) -> Optional[FileMetadata]:
        """Index a Python file (metadata only, no code content)."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠️  Error reading {file_path}: {e}")
            return None
        
        relative_path = os.path.relpath(file_path, repo_root)
        
        file_metadata = FileMetadata(
            file_path=file_path,
            relative_path=relative_path,
            language=CodeLanguage.PYTHON,
            total_lines=len(content.splitlines())
        )
        
        # Parse with AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return file_metadata
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_metadata.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_metadata.imports.append(node.module)
        
        # Extract top-level elements (metadata only)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                element = self._extract_class_metadata(node, file_path)
                file_metadata.elements.append(element)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                element = self._extract_function_metadata(node, file_path)
                file_metadata.elements.append(element)
        
        # BOTTOM-UP: Generate file summary if requested (with caching)
        if generate_summaries:
            # Use file hash for caching
            file_hash = self._hash_file(file_path)
            if file_hash in self.summary_cache:
                file_metadata.summary = self.summary_cache[file_hash]
            else:
                # Will be generated in batch later
                file_metadata.summary = None
                file_metadata.file_hash = file_hash  # Store hash for batch processing
        
        return file_metadata
    
    def _extract_class_metadata(self, node: ast.ClassDef, file_path: str) -> CodeElementMetadata:
        """Extract class metadata (no code content)."""
        
        element = CodeElementMetadata(
            name=node.name,
            element_type=CodeElementType.CLASS,
            file_path=file_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            is_public=not node.name.startswith('_')
        )
        
        # Extract methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._extract_function_metadata(item, file_path, is_method=True)
                element.children.append(method)
        
        return element
    
    def _extract_function_metadata(
        self,
        node: ast.FunctionDef,
        file_path: str,
        is_method: bool = False
    ) -> CodeElementMetadata:
        """Extract function/method metadata (no code content)."""
        
        # Build signature
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"
        
        element = CodeElementMetadata(
            name=node.name,
            element_type=CodeElementType.METHOD if is_method else CodeElementType.FUNCTION,
            file_path=file_path,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=signature,
            complexity=self._calculate_complexity(node),
            is_public=not node.name.startswith('_')
        )
        
        return element
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _get_index_filename(self, relative_path: str) -> str:
        """Generate index filename for a directory (always index.json)."""
        # In hierarchical structure, every directory has index.json
        return 'index.json'
    
    def _calculate_statistics(self, repo_index: RepositoryIndex, root_index: DirectoryIndex, index_dir: str):
        """Calculate repository statistics by traversing all directory indices."""
        
        def traverse(dir_index: DirectoryIndex):
            repo_index.total_directories += 1
            repo_index.total_files += dir_index.direct_file_count
            repo_index.total_lines += sum(f.total_lines for f in dir_index.files)
            
            # Count elements
            for file in dir_index.files:
                for element in file.elements:
                    if element.element_type == CodeElementType.CLASS:
                        repo_index.total_classes += 1
                        repo_index.total_methods += len(element.children)
                    elif element.element_type == CodeElementType.FUNCTION:
                        repo_index.total_functions += 1
                
                # Collect external dependencies
                for imp in file.imports:
                    if '.' not in imp and imp not in ['os', 'sys', 'json', 're']:
                        if imp not in repo_index.external_dependencies:
                            repo_index.external_dependencies.append(imp)
            
            # Recursively traverse subdirectories
            for subdir_ref in dir_index.subdirectories:
                # Load subdirectory index
                with open(subdir_ref.index_file_path, 'r') as f:
                    subdir_data = json.load(f)
                    subdir_index = DirectoryIndex(**subdir_data)
                    traverse(subdir_index)
        
        traverse(root_index)
    
    def _generate_file_summary(self, file_path: str, file_metadata: FileMetadata) -> str:
        """Generate LLM summary for a file (bottom-up: file level)."""
        
        if not file_metadata.elements:
            return f"Python file with {file_metadata.total_lines} lines"
        
        elements_desc = []
        for element in file_metadata.elements[:10]:
            if element.element_type == CodeElementType.CLASS:
                elements_desc.append(f"- Class: {element.name} ({len(element.children)} methods)")
            else:
                elements_desc.append(f"- {element.element_type.value}: {element.name}")
        
        imports_str = ', '.join(file_metadata.imports[:5]) if file_metadata.imports else 'none'
        
        prompt = f"""Summarize this Python file in one concise sentence:

File: {file_metadata.relative_path}
Lines: {file_metadata.total_lines}
Imports: {imports_str}

Code Elements:
{chr(10).join(elements_desc)}

Provide ONE sentence describing the file's purpose and main functionality."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Contains {len(file_metadata.elements)} code elements"
    
    def _generate_directory_summary(self, dir_index: DirectoryIndex) -> str:
        """Generate LLM summary for a directory (bottom-up: aggregates file summaries)."""
        
        # Collect file summaries from this directory
        file_summaries = []
        for file in dir_index.files[:10]:
            if file.summary:
                file_summaries.append(f"- {file.relative_path}: {file.summary}")
        
        # Collect subdirectory summaries
        subdir_summaries = []
        for subdir in dir_index.subdirectories[:5]:
            if subdir.summary:
                subdir_summaries.append(f"- {subdir.relative_path}/: {subdir.summary}")
        
        if not file_summaries and not subdir_summaries:
            return f"Directory with {len(dir_index.files)} files"
        
        prompt = f"""Summarize this code directory in one concise sentence based on its contents:

Directory: {dir_index.relative_path}
Files: {len(dir_index.files)}
Subdirectories: {len(dir_index.subdirectories)}

File Summaries:
{chr(10).join(file_summaries) if file_summaries else '(no files)'}

Subdirectory Summaries:
{chr(10).join(subdir_summaries) if subdir_summaries else '(no subdirs)'}

Provide ONE sentence describing what this directory contains and its purpose in the codebase."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Directory with {len(dir_index.files)} files and {len(dir_index.subdirectories)} subdirectories"
    
    def _generate_repo_summary(self, repo_index: RepositoryIndex, root_index: DirectoryIndex) -> str:
        """Generate repository summary (bottom-up: aggregates directory summaries)."""
        
        # Collect top-level directory summaries
        dir_summaries = []
        for subdir in root_index.subdirectories[:10]:
            if subdir.summary:
                dir_summaries.append(f"- {subdir.relative_path}/: {subdir.summary}")
        
        # Collect top-level file summaries
        file_summaries = []
        for file in root_index.files[:5]:
            if file.summary:
                file_summaries.append(f"- {file.relative_path}: {file.summary}")
        
        prompt = f"""Summarize this code repository based on its structure and contents:

Repository: {repo_index.name}
Files: {repo_index.total_files}
Lines: {repo_index.total_lines:,}
Classes: {repo_index.total_classes}
Functions: {repo_index.total_functions}
Methods: {repo_index.total_methods}
Dependencies: {', '.join(repo_index.external_dependencies[:10])}

Top-Level Directories:
{chr(10).join(dir_summaries) if dir_summaries else '(no directories)'}

Root Files:
{chr(10).join(file_summaries) if file_summaries else '(no root files)'}

Provide a 2-3 sentence summary describing what this repository does and its main purpose."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"A {repo_index.primary_language} repository with {repo_index.total_files} files"
    
    def _generate_id(self, path: str) -> str:
        """Generate unique ID for a path."""
        return hashlib.md5(path.encode()).hexdigest()[:12]
    
    def _hash_file(self, file_path: str) -> str:
        """Generate hash for file content (for caching)."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def _batch_generate_file_summaries(self, files: List[FileMetadata]) -> None:
        """Generate summaries for multiple files in parallel."""
        if not files:
            return
        
        # Filter files that need summaries
        files_to_summarize = [f for f in files if not f.summary and hasattr(f, 'file_hash')]
        
        if not files_to_summarize:
            return
        
        print(f"  🚀 Generating {len(files_to_summarize)} file summaries in parallel...")
        
        def generate_one_summary(file_metadata: FileMetadata) -> tuple:
            """Generate summary for one file."""
            try:
                summary = self._generate_file_summary_sync(file_metadata.file_path, file_metadata)
                return (file_metadata.file_hash, summary, file_metadata)
            except Exception as e:
                return (file_metadata.file_hash, f"Contains {len(file_metadata.elements)} code elements", file_metadata)
        
        # Use ThreadPoolExecutor for parallel LLM calls
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(generate_one_summary, f): f for f in files_to_summarize}
            
            for future in as_completed(futures):
                file_hash, summary, file_metadata = future.result()
                file_metadata.summary = summary
                self.summary_cache[file_hash] = summary
    
    def _generate_file_summary_sync(self, file_path: str, file_metadata: FileMetadata) -> str:
        """Generate LLM summary for a file (synchronous version for parallel execution)."""
        
        if not file_metadata.elements:
            return f"Python file with {file_metadata.total_lines} lines"
        
        elements_desc = []
        for element in file_metadata.elements[:10]:
            if element.element_type == CodeElementType.CLASS:
                elements_desc.append(f"- Class: {element.name} ({len(element.children)} methods)")
            else:
                elements_desc.append(f"- {element.element_type.value}: {element.name}")
        
        imports_str = ', '.join(file_metadata.imports[:5]) if file_metadata.imports else 'none'
        
        prompt = f"""Summarize this Python file in one concise sentence:

File: {file_metadata.relative_path}
Lines: {file_metadata.total_lines}
Imports: {imports_str}

Code Elements:
{chr(10).join(elements_desc)}

Provide ONE sentence describing the file's purpose and main functionality."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=80
        )
        return response.choices[0].message.content.strip()
