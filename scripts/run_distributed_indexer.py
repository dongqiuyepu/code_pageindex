"""
Run Distributed Code Indexer
Creates separate index files for each directory.
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.distributed_indexer import DistributedCodeIndexer


def main():
    """Run distributed indexer on openai-python repository."""
    
    # Load environment variables from parent directory
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(parent_dir, '.env')
    load_dotenv(env_path)
    
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    # Paths
    repo_path = os.path.join(parent_dir, 'repo', 'openai-python')
    output_dir = os.path.join(parent_dir, 'output', 'distributed_index')
    
    # Create indexer with optimized parallel processing
    indexer = DistributedCodeIndexer(
        api_key=api_key,
        base_url=base_url,
        model="gpt-4o-mini",
        max_workers=10  # Parallel workers for faster indexing
    )
    
    # Index repository
    repo_index = indexer.index_repository(
        repo_path=repo_path,
        output_dir=output_dir,
        generate_summaries=True
    )
    
    print(f"\n✅ Indexing complete!")
    print(f"\nRepository Index: {output_dir}/repo_index.json")
    print(f"Directory Indices: Hierarchical structure (mirrors repo)")
    print(f"\nStatistics:")
    print(f"  Total files: {repo_index.total_files}")
    print(f"  Total directories: {repo_index.total_directories}")
    print(f"  Total lines: {repo_index.total_lines:,}")
    print(f"  Total classes: {repo_index.total_classes}")
    print(f"  Total functions: {repo_index.total_functions}")
    print(f"  Total methods: {repo_index.total_methods}")
    
    print(f"\n📁 Hierarchical Index Structure:")
    print(f"  {output_dir}/")
    print(f"    ├── repo_index.json              (repository metadata)")
    print(f"    ├── index.json                   (root directory)")
    print(f"    └── src/")
    print(f"        ├── index.json               (src/ directory)")
    print(f"        └── openai/")
    print(f"            ├── index.json           (src/openai/ directory)")
    print(f"            └── resources/")
    print(f"                └── index.json       (src/openai/resources/)")
    print(f"\n💡 Each directory has its own index.json file")
    print(f"💡 Structure mirrors the code repository exactly")


if __name__ == "__main__":
    main()
