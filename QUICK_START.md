# Quick Start Guide - Distributed Code Indexer

## 🚀 Run the Indexer

### Basic Usage

```bash
cd /Users/dongqiuyepu/Desktop/code/python/pydantic-agent/code_pageindex
python scripts/run_distributed_indexer.py
```

This will:
1. ✅ Index the `openai-python` repository
2. ✅ Generate hierarchical index structure
3. ✅ Create LLM summaries for files and directories
4. ✅ Use parallel processing (10 workers) for speed

### Expected Output

```
================================================================================
DISTRIBUTED CODE INDEXER
================================================================================
Repository: /path/to/openai-python
Output: /path/to/distributed_index
Summaries: True
================================================================================

📁 Indexing directory: .
  ✓ Indexed: setup.py (5 elements)
  ✓ Indexed: README.md (0 elements)
  🚀 Generating 2 file summaries in parallel...
  🤖 Generating summary for .

📁 Indexing directory: src
  ✓ Indexed: src/__init__.py (3 elements)
  🚀 Generating 1 file summaries in parallel...
  🤖 Generating summary for src

📁 Indexing directory: src/openai
  ✓ Indexed: src/openai/_client.py (15 elements)
  ✓ Indexed: src/openai/_auth.py (8 elements)
  🚀 Generating 2 file summaries in parallel...
  🤖 Generating summary for src/openai
  ...

✅ Indexing complete!

Repository Index: distributed_index/repo_index.json
Directory Indices: Hierarchical structure (mirrors repo)

Statistics:
  Total files: 200
  Total directories: 50
  Total lines: 45,000
  Total classes: 150
  Total functions: 300
  Total methods: 800

📁 Hierarchical Index Structure:
  distributed_index/
    ├── repo_index.json              (repository metadata)
    ├── index.json                   (root directory)
    └── src/
        ├── index.json               (src/ directory)
        └── openai/
            ├── index.json           (src/openai/ directory)
            └── resources/
                └── index.json       (src/openai/resources/)

💡 Each directory has its own index.json file
💡 Structure mirrors the code repository exactly
```

## ⚙️ Configuration

### 1. Environment Setup

Make sure you have a `.env` file with your OpenAI API key:

```bash
# .env file
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
```

### 2. Adjust Parallelism

Edit `run_distributed_indexer.py` to change the number of parallel workers:

```python
indexer = DistributedCodeIndexer(
    api_key=api_key,
    base_url=base_url,
    model="gpt-4o-mini",
    max_workers=20  # Increase for faster indexing (if API allows)
)
```

**Recommendations**:
- Small repos (<100 files): `max_workers=5`
- Medium repos (100-500 files): `max_workers=10` (default)
- Large repos (>500 files): `max_workers=20`

### 3. Skip Summaries (Fast Mode)

For testing or when you don't need summaries:

```python
repo_index = indexer.index_repository(
    repo_path=repo_path,
    output_dir=output_dir,
    generate_summaries=False  # Skip LLM calls - very fast!
)
```

### 4. Index Different Repository

Edit the `repo_path` in `run_distributed_indexer.py`:

```python
# Change this line:
repo_path = os.path.join(os.path.dirname(__file__), 'repo', 'openai-python')

# To your repository:
repo_path = '/path/to/your/repository'
```

## 📊 Performance

### Typical Indexing Times

| Repository Size | Files | Time (First Run) | Time (Re-run) |
|----------------|-------|------------------|---------------|
| Small | <50 | ~30 seconds | ~10 seconds |
| Medium | 50-200 | ~2 minutes | ~30 seconds |
| Large | 200-500 | ~5 minutes | ~1 minute |
| Very Large | >500 | ~10 minutes | ~2 minutes |

**Note**: Re-run times are much faster due to caching!

## 🔍 Verify Results

### Check Index Files

```bash
# View repository index
cat distributed_index/repo_index.json | jq

# View root directory index
cat distributed_index/index.json | jq

# View specific directory
cat distributed_index/src/openai/index.json | jq

# List all index files
find distributed_index -name "index.json"
```

### Explore Structure

```bash
# See hierarchical structure
tree distributed_index -L 3

# Count index files
find distributed_index -name "index.json" | wc -l

# Check file sizes
du -sh distributed_index
```

## 🤖 Use with Agent

After indexing, run the agent:

```bash
python scripts/run_distributed_agent.py
```

The agent will automatically use the hierarchical index structure for navigation.

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY not found"

**Solution**: Create a `.env` file with your API key:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### Error: "RateLimitError"

**Solution**: Reduce `max_workers`:
```python
max_workers=5  # Lower number of parallel workers
```

### Slow Indexing

**Solutions**:
1. Increase `max_workers` (if API allows)
2. Use faster model: `model="gpt-3.5-turbo"`
3. Skip summaries: `generate_summaries=False`

### Out of Memory

**Solution**: Reduce `max_workers`:
```python
max_workers=5  # Use fewer parallel workers
```

## 📚 Next Steps

1. **Index your repository**: Modify `repo_path` and run the script
2. **Explore the index**: Use `cat` and `jq` to view index files
3. **Run the agent**: Use `run_distributed_agent.py` to query the index
4. **Read documentation**:
   - `HIERARCHICAL_INDEX.md` - Hierarchical structure details
   - `PERFORMANCE_OPTIMIZATION.md` - Performance improvements
   - `AGENT_UPDATE.md` - Agent integration

## 💡 Tips

### Tip 1: Use jq for Better Viewing

```bash
# Install jq (if not installed)
brew install jq  # macOS
sudo apt-get install jq  # Linux

# View formatted JSON
cat distributed_index/index.json | jq '.'

# Extract specific fields
cat distributed_index/index.json | jq '.files[] | {name: .relative_path, summary: .summary}'
```

### Tip 2: Cache Summaries

The indexer caches summaries automatically. Re-running the indexer on unchanged files is very fast!

### Tip 3: Incremental Updates

If you modify a few files, just re-run the indexer. Only changed files will regenerate summaries.

### Tip 4: Monitor Progress

Watch for these indicators:
- `✓ Indexed:` - File indexed
- `🚀 Generating N file summaries in parallel...` - Batch processing
- `🤖 Generating summary for` - Directory summary

## 🎯 Summary

**To index a repository**:
```bash
python scripts/run_distributed_indexer.py
```

**To query the index**:
```bash
python scripts/run_distributed_agent.py
```

That's it! The indexer is optimized and ready to use. 🚀
