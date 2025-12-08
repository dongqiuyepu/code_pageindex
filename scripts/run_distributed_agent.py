"""
Run Distributed Code Agent
Uses distributed index structure (separate file per directory).
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.distributed_agent import create_distributed_agent
from src.distributed_indexer import DistributedCodeIndexer


def build_index_if_missing(repo_path: str, output_dir: str, api_key: str, base_url: str):
    """Build distributed index if it doesn't exist."""
    
    repo_index_path = os.path.join(output_dir, "repo_index.json")
    
    if os.path.exists(repo_index_path):
        print(f"✓ Found existing index: {repo_index_path}")
        return
    
    print(f"Building distributed index for {repo_path}...")
    
    indexer = DistributedCodeIndexer(
        api_key=api_key,
        base_url=base_url,
        model="gpt-4o-mini"
    )
    
    indexer.index_repository(
        repo_path=repo_path,
        output_dir=output_dir,
        generate_summaries=True
    )
    
    print(f"✓ Index built successfully")


def main():
    """Run distributed code agent."""
    
    # Load environment variables from parent directory
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    env_path = os.path.join(parent_dir, '.env')
    load_dotenv(env_path)
    
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    
    if not api_key or not base_url:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    # Set OpenAI API key for agent
    os.environ['OPENAI_API_KEY'] = api_key
    if base_url:
        os.environ['OPENAI_BASE_URL'] = base_url
    
    # Paths
    repo_path = os.path.join(parent_dir, 'repo', 'openai-python')
    output_dir = os.path.join(parent_dir, 'output', 'distributed_index')
    
    # Build index if missing
    build_index_if_missing(repo_path, output_dir, api_key, base_url)
    
    # Create agent
    print(f"\nCreating distributed code agent...")
    agent = create_distributed_agent(
        index_root_dir=output_dir,
        model="gpt-4o",
        verbose=True
    )
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Single query mode
        question = ' '.join(sys.argv[1:])
        result = agent.query(question)
    else:
        # Interactive mode
        agent.interactive()


if __name__ == "__main__":
    main()
