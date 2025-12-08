# Hierarchical Distributed Index Structure

## Overview

The optimized distributed index creates a **hierarchical folder structure that mirrors the code repository**, with proper **bottom-up summarization** at every level.

## Key Improvements

### 1. Hierarchical Folder Structure

**Before** (Flat structure):
```
distributed_index/
└── .index/
    ├── root_index.json
    ├── src_index.json
    ├── src_openai_index.json
    ├── src_openai_resources_index.json
    └── ... (all in one flat directory)
```

**After** (Hierarchical structure):
```
distributed_index/
├── repo_index.json
├── index.json                    # Root directory index
├── src/
│   ├── index.json                # src/ directory index
│   └── openai/
│       ├── index.json            # src/openai/ directory index
│       ├── resources/
│       │   ├── index.json        # src/openai/resources/ index
│       │   ├── audio/
│       │   │   └── index.json    # src/openai/resources/audio/ index
│       │   ├── beta/
│       │   │   └── index.json
│       │   └── uploads/
│       │       └── index.json
│       ├── types/
│       │   └── index.json
│       └── lib/
│           └── index.json
├── examples/
│   └── index.json
└── scripts/
    └── index.json
```

### 2. Bottom-Up Indexing Flow

```
1. Index leaf directories first (deepest level)
   └─> src/openai/resources/uploads/
       ├─ Index all .py files
       ├─ Generate file summaries
       ├─ Calculate directory statistics
       └─ Generate directory summary
       └─> Save: src/openai/resources/uploads/index.json

2. Index parent directories (using child summaries)
   └─> src/openai/resources/
       ├─ Index all .py files in this directory
       ├─ Reference child directories (uploads/, audio/, beta/)
       ├─ Aggregate statistics from children
       ├─ Generate directory summary (using child summaries)
       └─> Save: src/openai/resources/index.json

3. Continue up the tree
   └─> src/openai/
       └─> src/
           └─> root (.)
               └─> repo_index.json
```

## File Structure

### Repository Index (`repo_index.json`)

Located at the root of the index directory:

```json
{
  "repo_id": "abc123",
  "name": "openai-python",
  "repo_path": "/path/to/openai-python",
  "index_root_path": "/path/to/distributed_index",
  "root_index_path": "/path/to/distributed_index/index.json",
  "summary": "Comprehensive Python SDK for OpenAI API...",
  "total_files": 500,
  "total_directories": 44,
  "total_lines": 65639,
  "total_classes": 928,
  "total_functions": 467,
  "total_methods": 1930
}
```

### Directory Index (`index.json`)

Every directory has an `index.json` file:

```json
{
  "dir_path": "/path/to/src/openai/resources",
  "relative_path": "src/openai/resources",
  "index_file_path": "/path/to/distributed_index/src/openai/resources/index.json",
  "parent_index_path": "/path/to/distributed_index/src/openai/index.json",
  "summary": "API resource implementations for OpenAI SDK...",
  
  "files": [
    {
      "relative_path": "src/openai/resources/__init__.py",
      "summary": "Exports all resource modules",
      "total_lines": 173,
      "elements": []
    },
    {
      "relative_path": "src/openai/resources/batches.py",
      "summary": "Batch processing classes for async and sync operations",
      "total_lines": 517,
      "elements": [
        {
          "name": "Batches",
          "element_type": "class",
          "children": [
            {"name": "create", "element_type": "method"},
            {"name": "retrieve", "element_type": "method"}
          ]
        }
      ]
    }
  ],
  
  "subdirectories": [
    {
      "dir_name": "audio",
      "dir_path": "/path/to/src/openai/resources/audio",
      "relative_path": "src/openai/resources/audio",
      "index_file_path": "/path/to/distributed_index/src/openai/resources/audio/index.json",
      "summary": "Audio processing and transcription modules",
      "file_count": 5,
      "subdir_count": 0
    },
    {
      "dir_name": "uploads",
      "index_file_path": "/path/to/distributed_index/src/openai/resources/uploads/index.json",
      "summary": "File upload management classes",
      "file_count": 3,
      "subdir_count": 0
    }
  ],
  
  "direct_file_count": 12,
  "total_file_count": 45,
  "total_lines": 5234
}
```

## Navigation Examples

### Example 1: Navigate to Specific Directory

**Goal**: Find `src/openai/resources/uploads/` directory

```bash
# 1. Load repository index
cat distributed_index/repo_index.json
# → Get root_index_path: "distributed_index/index.json"

# 2. Load root directory
cat distributed_index/index.json
# → Find "src" subdirectory reference

# 3. Load src directory
cat distributed_index/src/index.json
# → Find "openai" subdirectory reference

# 4. Load src/openai directory
cat distributed_index/src/openai/index.json
# → Find "resources" subdirectory reference

# 5. Load src/openai/resources directory
cat distributed_index/src/openai/resources/index.json
# → Find "uploads" subdirectory reference

# 6. Load src/openai/resources/uploads directory
cat distributed_index/src/openai/resources/uploads/index.json
# → See all files in this directory (inline)
```

### Example 2: Agent Navigation

```bash
# Agent starts at repository level
cat distributed_index/repo_index.json

# Agent sees summary: "Comprehensive Python SDK for OpenAI API..."
# Agent decides to explore "src" directory

cat distributed_index/index.json | jq '.subdirectories[] | select(.dir_name == "src")'
# → Get index_file_path: "distributed_index/src/index.json"

cat distributed_index/src/index.json
# → See summary: "Source code for OpenAI Python SDK..."
# → See subdirectories: ["openai"]

cat distributed_index/src/openai/index.json
# → See summary: "Core OpenAI SDK implementation..."
# → See subdirectories: ["resources", "types", "lib", "cli"]
# → See files: ["_client.py", "_auth.py", ...]

# Agent finds _client.py in files array (inline)
cat distributed_index/src/openai/index.json | jq '.files[] | select(.relative_path | contains("_client"))'
```

## Bottom-Up Summarization

### Level 1: File Summaries

```python
# Index file: src/openai/resources/uploads/parts.py
file_summary = generate_file_summary(
    file_path="src/openai/resources/uploads/parts.py",
    elements=["Parts class", "AsyncParts class"],
    imports=["io", "os", "typing"]
)
# → "Defines classes for handling file uploads in sync and async contexts"
```

### Level 2: Directory Summaries (Using File Summaries)

```python
# Index directory: src/openai/resources/uploads/
directory_summary = generate_directory_summary(
    directory="src/openai/resources/uploads",
    file_summaries=[
        "parts.py: Defines classes for handling file uploads...",
        "uploads.py: Upload management with progress tracking..."
    ],
    subdirectories=[]  # Leaf directory
)
# → "File upload management with sync and async support"
```

### Level 3: Parent Directory Summaries (Using Child Summaries)

```python
# Index directory: src/openai/resources/
directory_summary = generate_directory_summary(
    directory="src/openai/resources",
    file_summaries=[
        "batches.py: Batch processing classes...",
        "completions.py: Text completion endpoints..."
    ],
    subdirectory_summaries=[
        "audio/: Audio processing and transcription modules",
        "uploads/: File upload management with sync and async support",
        "beta/: Beta API features and experimental functionality"
    ]
)
# → "API resource implementations including audio, uploads, and beta features"
```

### Level 4: Repository Summary (Using Top-Level Summaries)

```python
# Repository summary
repo_summary = generate_repo_summary(
    repository="openai-python",
    directory_summaries=[
        "src/: Source code for OpenAI Python SDK",
        "examples/: Usage examples and demonstrations",
        "scripts/: Build and utility scripts"
    ],
    statistics={
        "files": 500,
        "lines": 65639,
        "classes": 928
    }
)
# → "Comprehensive Python SDK for OpenAI API with extensive resource implementations"
```

## Benefits

### 1. True Hierarchical Structure

- **Mirrors code repository**: Index structure matches code structure
- **Intuitive navigation**: Navigate like you would in a file browser
- **Clear parent-child relationships**: Each directory knows its parent and children

### 2. Proper Bottom-Up Summarization

- **Leaf directories first**: Index deepest directories before parents
- **Aggregate information**: Parent summaries use child summaries
- **Accurate context**: Each level has complete information from below
- **No information loss**: All details bubble up correctly

### 3. Agent-Friendly Navigation

- **Natural path traversal**: Follow directory structure naturally
- **Contextual exploration**: See summary at each level before diving deeper
- **Efficient discovery**: Load only the directories you need
- **Clear breadcrumbs**: Always know where you are in the tree

### 4. Scalability

- **Distributed files**: Each directory has its own index
- **Parallel loading**: Load multiple directories simultaneously
- **Incremental updates**: Update only changed directories
- **Memory efficient**: Load only current path, not entire tree

## Comparison

### Old Flat Structure

```
.index/
├── root_index.json
├── src_index.json
├── src_openai_index.json
├── src_openai_resources_index.json
├── src_openai_resources_audio_index.json
├── src_openai_resources_uploads_index.json
└── ... (44 files in one directory)
```

**Problems**:
- ❌ Flat namespace (hard to navigate)
- ❌ Unclear relationships
- ❌ No visual hierarchy
- ❌ Difficult to find specific directory

### New Hierarchical Structure

```
/
├── repo_index.json
├── index.json
├── src/
│   ├── index.json
│   └── openai/
│       ├── index.json
│       └── resources/
│           ├── index.json
│           ├── audio/
│           │   └── index.json
│           └── uploads/
│               └── index.json
```

**Benefits**:
- ✅ Hierarchical namespace (easy to navigate)
- ✅ Clear parent-child relationships
- ✅ Visual hierarchy matches code
- ✅ Easy to find any directory

## Agent System Prompt

```
You have access to a HIERARCHICAL distributed code index:

STRUCTURE:
- Repository Index: distributed_index/repo_index.json
- Root Directory: distributed_index/index.json
- Subdirectories: distributed_index/{path}/index.json

Each directory has its own index.json file in a hierarchical structure
that mirrors the code repository.

NAVIGATION:
1. Start at repo_index.json for overview
2. Load root index.json
3. Navigate to subdirectories by following the path:
   - src/ → distributed_index/src/index.json
   - src/openai/ → distributed_index/src/openai/index.json
   - src/openai/resources/ → distributed_index/src/openai/resources/index.json

BOTTOM-UP SUMMARIES:
- File summaries describe individual files
- Directory summaries aggregate file and subdirectory summaries
- Repository summary aggregates top-level directory summaries
- All summaries are generated bottom-up for accuracy

EXAMPLE:
# Navigate to src/openai/resources/
cat distributed_index/repo_index.json
cat distributed_index/index.json
cat distributed_index/src/index.json
cat distributed_index/src/openai/index.json
cat distributed_index/src/openai/resources/index.json

# Files are inline in the directory index
jq '.files[]' distributed_index/src/openai/resources/index.json
```

## Implementation Details

### Indexing Order (Bottom-Up)

```python
def _index_directory(dir_path, repo_root, output_root):
    # 1. Index all files in this directory
    for file in files:
        file_metadata = index_file(file)
        file_metadata.summary = generate_file_summary(file_metadata)
    
    # 2. Recursively index subdirectories (BOTTOM-UP)
    for subdir in subdirectories:
        subdir_index = _index_directory(subdir, repo_root, output_root)
        # subdir_index already has its summary
    
    # 3. Generate directory summary (using file and subdir summaries)
    dir_summary = generate_directory_summary(
        files=[f.summary for f in file_metadata],
        subdirs=[s.summary for s in subdir_indices]
    )
    
    # 4. Save index to hierarchical location
    index_path = output_root / relative_path / "index.json"
    save_index(index_path, dir_index)
    
    return dir_index
```

### Index File Location

```python
def get_index_path(relative_path, output_root):
    if relative_path == '.':
        return output_root / "index.json"
    else:
        return output_root / relative_path / "index.json"

# Examples:
# "." → "distributed_index/index.json"
# "src" → "distributed_index/src/index.json"
# "src/openai" → "distributed_index/src/openai/index.json"
# "src/openai/resources" → "distributed_index/src/openai/resources/index.json"
```

## Summary

The optimized hierarchical distributed index provides:

1. **True hierarchical structure** that mirrors the code repository
2. **Proper bottom-up summarization** at every level
3. **Intuitive navigation** for both humans and agents
4. **Scalable architecture** for repositories of any size
5. **Clear parent-child relationships** throughout the tree

This makes it significantly easier for AI agents to navigate and understand large codebases systematically.
