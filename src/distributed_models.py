"""
Distributed Code Index Models
Each directory has its own index file with references to subdirectory indices and code files.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class CodeLanguage(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    OTHER = "other"


class CodeElementType(str, Enum):
    """Types of code elements."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class CodeElementMetadata(BaseModel):
    """Lightweight metadata for a code element (no code content)."""
    name: str = Field(..., description="Element name")
    element_type: CodeElementType = Field(..., description="Type of element")
    file_path: str = Field(..., description="Absolute path to source file")
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")
    summary: Optional[str] = Field(None, description="Brief description of what this element does")
    signature: Optional[str] = Field(None, description="Function/method signature")
    complexity: Optional[int] = Field(None, description="Cyclomatic complexity")
    is_public: bool = Field(True, description="Whether element is public")
    children: List['CodeElementMetadata'] = Field(default_factory=list, description="Child elements (e.g., methods in a class)")


class FileMetadata(BaseModel):
    """Lightweight metadata for a source file (no code content)."""
    file_path: str = Field(..., description="Absolute path to file")
    relative_path: str = Field(..., description="Relative path from repo root")
    language: CodeLanguage = Field(..., description="Programming language")
    summary: Optional[str] = Field(None, description="Summary of file purpose")
    total_lines: int = Field(0, description="Total lines in file")
    elements: List[CodeElementMetadata] = Field(default_factory=list, description="Top-level code elements")
    imports: List[str] = Field(default_factory=list, description="Import statements")
    exports: List[str] = Field(default_factory=list, description="Exported symbols")
    file_hash: Optional[str] = Field(None, description="Hash of file content for caching", exclude=True)


class SubdirectoryReference(BaseModel):
    """Reference to a subdirectory's index file."""
    dir_name: str = Field(..., description="Directory name")
    dir_path: str = Field(..., description="Absolute path to directory")
    relative_path: str = Field(..., description="Relative path from repo root")
    index_file_path: str = Field(..., description="Path to subdirectory's index file")
    summary: Optional[str] = Field(None, description="Summary of subdirectory purpose")
    file_count: int = Field(0, description="Number of files in subdirectory (recursive)")
    subdir_count: int = Field(0, description="Number of subdirectories (recursive)")


class DirectoryIndex(BaseModel):
    """
    Index for a single directory.
    Stored in a separate file for each directory.
    Contains references to subdirectory indices and code files.
    """
    # Directory info
    dir_path: str = Field(..., description="Absolute path to this directory")
    relative_path: str = Field(..., description="Relative path from repo root")
    index_file_path: str = Field(..., description="Path to this index file")
    
    # Summary
    summary: Optional[str] = Field(None, description="Summary of directory purpose")
    
    # Parent reference
    parent_index_path: Optional[str] = Field(None, description="Path to parent directory's index file")
    
    # Files in this directory (direct children only)
    files: List[FileMetadata] = Field(default_factory=list, description="Files in this directory")
    
    # Subdirectory references (not full content, just references)
    subdirectories: List[SubdirectoryReference] = Field(default_factory=list, description="References to subdirectory indices")
    
    # Statistics for this directory only
    direct_file_count: int = Field(0, description="Number of files directly in this directory")
    total_file_count: int = Field(0, description="Total files including subdirectories")
    total_lines: int = Field(0, description="Total lines of code including subdirectories")
    
    # Metadata
    indexed_at: datetime = Field(default_factory=datetime.now, description="When this directory was indexed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_file_paths(self) -> List[str]:
        """Get all file paths in this directory (direct children only)."""
        return [f.file_path for f in self.files]
    
    def get_subdirectory_index_paths(self) -> List[str]:
        """Get all subdirectory index file paths."""
        return [s.index_file_path for s in self.subdirectories]


class RepositoryIndex(BaseModel):
    """
    Root repository index.
    Contains metadata and reference to root directory index.
    """
    # Repository info
    repo_id: str = Field(..., description="Unique repository identifier")
    name: str = Field(..., description="Repository name")
    repo_path: str = Field(..., description="Absolute path to repository")
    index_root_path: str = Field(..., description="Root path where index files are stored")
    
    # Root directory index reference
    root_index_path: str = Field(..., description="Path to root directory's index file")
    
    # High-level metadata
    summary: Optional[str] = Field(None, description="Repository summary")
    architecture_description: Optional[str] = Field(None, description="Architecture overview")
    primary_language: str = Field("python", description="Primary programming language")
    
    # Global statistics
    total_files: int = Field(0, description="Total number of files")
    total_lines: int = Field(0, description="Total lines of code")
    total_classes: int = Field(0, description="Total number of classes")
    total_functions: int = Field(0, description="Total number of functions")
    total_methods: int = Field(0, description="Total number of methods")
    total_directories: int = Field(0, description="Total number of directories")
    
    # Quick lookup
    entry_points: List[str] = Field(default_factory=list, description="Entry point files")
    external_dependencies: List[str] = Field(default_factory=list, description="External dependencies")
    
    # Metadata
    indexed_at: datetime = Field(default_factory=datetime.now, description="When index was created")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
            "total_methods": self.total_methods,
            "total_directories": self.total_directories,
            "primary_language": self.primary_language,
            "external_dependencies": len(self.external_dependencies),
            "entry_points": len(self.entry_points)
        }
