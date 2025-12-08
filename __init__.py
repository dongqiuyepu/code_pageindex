"""
Code Repository PageIndex
Deep document indexing for code repositories using hierarchical structure.
"""

from .code_models import (
    CodeNode,
    CodeFile,
    DirectoryNode,
    RepositoryIndex,
    CodeSearchResult,
    CodeQuery,
    CodeQueryResponse,
    CodeLanguage,
    CodeElementType,
    CodeComplexity,
    CodeDependency
)

from .code_indexer import (
    CodeRepositoryIndexer,
    PythonCodeParser
)

from .code_retriever import CodeRetriever

__version__ = "0.1.0"

__all__ = [
    # Models
    "CodeNode",
    "CodeFile",
    "DirectoryNode",
    "RepositoryIndex",
    "CodeSearchResult",
    "CodeQuery",
    "CodeQueryResponse",
    "CodeLanguage",
    "CodeElementType",
    "CodeComplexity",
    "CodeDependency",
    
    # Indexer
    "CodeRepositoryIndexer",
    "PythonCodeParser",
    
    # Retriever
    "CodeRetriever",
]
