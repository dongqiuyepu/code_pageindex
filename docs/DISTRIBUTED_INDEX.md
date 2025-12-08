# Distributed Index Structure

## Overview

The distributed index structure stores each directory's index in a **separate file**, with references to subdirectory indices and code files. This approach provides better scalability, modularity, and navigation compared to a single monolithic index file.

## Architecture

### File Structure

```
distributed_index/
├── repo_index.json              # Repository metadata and root reference
└── .index/                      # Directory containing all index files
    ├── root_index.json          # Root directory index
    ├── src_index.json           # src/ directory index
    ├── src_openai_index.json    # src/openai/ directory index
    ├── examples_index.json      # examples/ directory index
    └── ...                      # One index file per directory
```

### Three-Level Hierarchy

```
Repository Index (repo_index.json)
    ↓ references
Root Directory Index (root_index.json)
    ↓ references
Subdirectory Indices (src_index.json, etc.)
    ↓ contains
File Metadata (inline in directory index)
```

## Index File Types

### 1. Repository Index (`repo_index.json`)

**Purpose**: Top-level metadata and reference to root directory index

**Contents**:
- Repository metadata (name, path, ID)
- Global statistics (total files, lines, classes, functions)
- Reference to root directory index
- External dependencies
- Entry points
- Repository summary

**Example**:
```json
{
  "repo_id": "abc123",
  "name": "openai-python",
  "repo_path": "/path/to/openai-python",
  "index_root_path": "/path/to/distributed_index/.index",
  "root_index_path": "/path/to/distributed_index/.index/root_index.json",
  "summary": "Comprehensive Python SDK for OpenAI API...",
  "total_files": 500,
  "total_lines": 65639,
  "total_classes": 928,
  "total_functions": 467,
  "total_methods": 1930,
  "total_directories": 45,
  "external_dependencies": ["httpx", "pydantic", "typing_extensions"]
}
```

### 2. Directory Index (`*_index.json`)

**Purpose**: Index for a single directory with references to children

**Contents**:
- Directory metadata (path, relative path)
- Parent index reference
- **File metadata** (inline, full details)
- **Subdirectory references** (not full content, just pointers)
- Directory summary
- Statistics for this directory

**Example** (`src_openai_index.json`):
```json
{
  "dir_path": "/path/to/openai-python/src/openai",
  "relative_path": "src/openai",
  "index_file_path": "/path/to/.index/src_openai_index.json",
  "parent_index_path": "/path/to/.index/src_index.json",
  "summary": "Core OpenAI SDK implementation with client and resources",
  
  "files": [
    {
      "file_path": "/path/to/src/openai/_client.py",
      "relative_path": "src/openai/_client.py",
      "language": "python",
      "summary": "Main OpenAI client class with API methods",
      "total_lines": 450,
      "elements": [
        {
          "name": "OpenAI",
          "element_type": "class",
          "start_line": 10,
          "end_line": 200,
          "children": [...]
        }
      ],
      "imports": ["httpx", "typing"]
    }
  ],
  
  "subdirectories": [
    {
      "dir_name": "resources",
      "dir_path": "/path/to/src/openai/resources",
      "relative_path": "src/openai/resources",
      "index_file_path": "/path/to/.index/src_openai_resources_index.json",
      "summary": "API resource implementations",
      "file_count": 25,
      "subdir_count": 3
    }
  ],
  
  "direct_file_count": 15,
  "total_file_count": 40,
  "total_lines": 5000
}
```

## Key Differences from Monolithic Index

### Monolithic Index (Old)

```json
{
  "repo_index": {
    "root_directory": {
      "subdirectories": [
        {
          "subdirectories": [
            {
              "subdirectories": [
                // Deeply nested...
              ]
            }
          ]
        }
      ]
    }
  }
}
```

**Problems**:
- ❌ Single massive file (10+ MB)
- ❌ Must load entire tree to access any part
- ❌ Hard to navigate deeply nested structure
- ❌ Slow to parse and load
- ❌ Difficult to update incrementally

### Distributed Index (New)

```
repo_index.json → root_index.json → src_index.json → src_openai_index.json
```

**Benefits**:
- ✅ Small, focused files (10-100 KB each)
- ✅ Load only what you need
- ✅ Flat file structure, easy to navigate
- ✅ Fast to parse individual files
- ✅ Easy to update individual directories

## Navigation Patterns

### Pattern 1: Top-Down Navigation

**Start**: Repository index
**Goal**: Find specific file

```python
# 1. Load repository index
repo_index = load_json("repo_index.json")

# 2. Load root directory index
root_index = load_json(repo_index["root_index_path"])

# 3. Find subdirectory reference
src_ref = find_subdir(root_index, "src")

# 4. Load subdirectory index
src_index = load_json(src_ref["index_file_path"])

# 5. Find file in directory
file = find_file(src_index, "_client.py")
```

### Pattern 2: Direct Access

**Start**: Know directory path
**Goal**: Access directory index directly

```python
# Direct access to specific directory
index_path = ".index/src_openai_index.json"
dir_index = load_json(index_path)

# Access files in this directory
for file in dir_index["files"]:
    print(file["relative_path"])
```

### Pattern 3: Breadth-First Search

**Start**: Repository index
**Goal**: Find all files matching criteria

```python
# 1. Load root index
root_index = load_json(repo_index["root_index_path"])

# 2. Queue of directory indices to process
queue = [root_index]

# 3. Process each directory
while queue:
    dir_index = queue.pop(0)
    
    # Search files in this directory
    for file in dir_index["files"]:
        if matches_criteria(file):
            results.append(file)
    
    # Add subdirectories to queue
    for subdir_ref in dir_index["subdirectories"]:
        subdir_index = load_json(subdir_ref["index_file_path"])
        queue.append(subdir_index)
```

### Pattern 4: Parent Navigation

**Start**: Current directory index
**Goal**: Navigate to parent

```python
# Load current directory
current_index = load_json("src_openai_index.json")

# Navigate to parent
parent_index = load_json(current_index["parent_index_path"])
```

## Agent Integration

### Agent Workflow

**Step 1: Start with Repository Index**
```bash
cat distributed_index/repo_index.json
# Get overview: total files, directories, summary
```

**Step 2: Navigate to Relevant Directory**
```bash
# Agent reads root index
cat distributed_index/.index/root_index.json

# Finds "src" subdirectory reference
# Loads src directory index
cat distributed_index/.index/src_index.json
```

**Step 3: Drill Down to Specific Files**
```bash
# Agent finds "openai" subdirectory
cat distributed_index/.index/src_openai_index.json

# Reads file metadata inline
# Decides which files to read
cat /path/to/src/openai/_client.py
```

### Agent System Prompt

```
You have access to a distributed code index with the following structure:

1. Repository Index: distributed_index/repo_index.json
   - Contains repository metadata and reference to root directory index
   - Use this to understand overall repository structure

2. Directory Indices: distributed_index/.index/*_index.json
   - Each directory has its own index file
   - Contains file metadata (inline) and subdirectory references (pointers)
   - Use these to navigate the codebase

3. Code Files: Full source code at file_path
   - Read actual code when you need implementation details

Navigation Strategy:
1. Start with repo_index.json to understand structure
2. Load root_index.json to see top-level directories
3. Follow subdirectory references to drill down
4. Read file metadata inline in directory indices
5. Read actual code files when needed

Example:
cat distributed_index/repo_index.json
cat distributed_index/.index/root_index.json
cat distributed_index/.index/src_openai_index.json
cat /path/to/src/openai/_client.py
```

## Benefits

### 1. Scalability

**Monolithic**:
- 10 MB single file for 500 files
- 100 MB for 5,000 files
- Unmanageable for large repos

**Distributed**:
- 50 KB per directory index
- 45 directories × 50 KB = 2.25 MB total
- Scales linearly with directory count

### 2. Performance

**Monolithic**:
- Load entire 10 MB file to access any part
- Parse entire JSON tree
- Slow for large repositories

**Distributed**:
- Load only needed indices (50-100 KB each)
- Parse small JSON files quickly
- Fast even for large repositories

### 3. Modularity

**Monolithic**:
- Single point of failure
- Hard to update incrementally
- Must regenerate entire index

**Distributed**:
- Independent index files
- Update only changed directories
- Incremental indexing possible

### 4. Navigation

**Monolithic**:
- Navigate nested JSON structure
- Hard to find specific directories
- Deep nesting is confusing

**Distributed**:
- Flat file structure
- Direct access to any directory
- Clear parent-child relationships

### 5. Memory Efficiency

**Monolithic**:
- Load entire tree into memory
- High memory usage
- May cause issues on limited systems

**Distributed**:
- Load only current directory
- Low memory footprint
- Efficient for constrained environments

## Index File Naming

### Convention

```
{relative_path_with_underscores}_index.json
```

### Examples

| Directory | Relative Path | Index Filename |
|-----------|---------------|----------------|
| Root | `.` | `root_index.json` |
| `src/` | `src` | `src_index.json` |
| `src/openai/` | `src/openai` | `src_openai_index.json` |
| `src/openai/resources/` | `src/openai/resources` | `src_openai_resources_index.json` |
| `examples/` | `examples` | `examples_index.json` |

### Special Cases

- Replace `/` with `_`
- Replace `.` with `_` (except for root)
- Remove special characters
- Always ends with `_index.json`

## Bottom-Up Indexing

The distributed indexer uses **bottom-up** summarization:

### Step 1: Index Leaf Directories

```
examples/
  ├── assistant.py
  └── chat.py

→ examples_index.json (with file summaries)
```

### Step 2: Index Parent Directories

```
src/openai/
  ├── _client.py
  ├── _auth.py
  └── resources/ → src_openai_resources_index.json (already indexed)

→ src_openai_index.json (aggregates subdirectory summaries)
```

### Step 3: Index Root

```
root/
  ├── setup.py
  ├── src/ → src_index.json (already indexed)
  └── examples/ → examples_index.json (already indexed)

→ root_index.json (aggregates all subdirectory summaries)
```

### Step 4: Create Repository Index

```
Repository
  └── root/ → root_index.json (already indexed)

→ repo_index.json (aggregates from root summary)
```

## Usage

### Build Distributed Index

```bash
python run_distributed_indexer.py
```

**Output**:
```
distributed_index/
├── repo_index.json
└── .index/
    ├── root_index.json
    ├── src_index.json
    ├── src_openai_index.json
    └── ...
```

### Load and Navigate

```python
import json

# Load repository index
with open('distributed_index/repo_index.json') as f:
    repo_index = json.load(f)

print(f"Repository: {repo_index['name']}")
print(f"Total files: {repo_index['total_files']}")

# Load root directory index
with open(repo_index['root_index_path']) as f:
    root_index = json.load(f)

print(f"\nTop-level directories:")
for subdir in root_index['subdirectories']:
    print(f"  - {subdir['dir_name']}: {subdir['summary']}")
    
# Load specific directory
with open('.index/src_openai_index.json') as f:
    src_openai_index = json.load(f)

print(f"\nFiles in src/openai/:")
for file in src_openai_index['files']:
    print(f"  - {file['relative_path']}: {file['summary']}")
```

## Comparison Table

| Aspect | Monolithic Index | Distributed Index |
|--------|------------------|-------------------|
| **File Count** | 1 file | 1 + N files (N = directories) |
| **File Size** | 10+ MB | 50-100 KB per file |
| **Load Time** | Slow (entire tree) | Fast (only needed parts) |
| **Memory Usage** | High (entire tree) | Low (current directory) |
| **Navigation** | Nested traversal | Direct file access |
| **Scalability** | Poor (grows exponentially) | Good (grows linearly) |
| **Updates** | Regenerate entire index | Update only changed directories |
| **Agent-Friendly** | Complex nested structure | Simple flat structure |
| **Incremental** | No | Yes (possible) |

## Future Enhancements

### 1. Incremental Indexing

Only re-index changed directories:
```python
# Detect changed files
changed_dirs = detect_changes(repo_path, last_index_time)

# Re-index only changed directories
for dir_path in changed_dirs:
    reindex_directory(dir_path)
```

### 2. Lazy Loading

Load indices on-demand:
```python
class LazyDirectoryIndex:
    def __init__(self, index_path):
        self.index_path = index_path
        self._data = None
    
    @property
    def data(self):
        if self._data is None:
            self._data = load_json(self.index_path)
        return self._data
```

### 3. Index Caching

Cache frequently accessed indices:
```python
index_cache = {}

def load_index(path):
    if path not in index_cache:
        index_cache[path] = load_json(path)
    return index_cache[path]
```

### 4. Parallel Indexing

Index directories in parallel:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(index_directory, d) for d in directories]
    results = [f.result() for f in futures]
```

---

**The distributed index structure provides a scalable, efficient, and agent-friendly way to index and navigate large code repositories.**
