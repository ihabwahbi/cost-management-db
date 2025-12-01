#!/usr/bin/env python3
"""
XLSX Caching Utilities for Pipeline Scripts

Provides a robust caching mechanism for xlsx-to-csv pipeline stages.
The cache uses the Stage output CSV as the artifact and stores metadata
in a sidecar JSON file.

Cache Validation Checks:
1. Output CSV must exist
2. Metadata sidecar must exist and be valid JSON
3. Source xlsx filename must match (different file = invalidate)
4. Source mtime and size must match (modified file = invalidate)
5. Script dependencies hash must match (code change = invalidate)

Usage:
    from utils.xlsx_cache import XlsxCacheManager

    cache = XlsxCacheManager(
        source_dir=RAW_DIR,
        source_pattern="ProjectDashboard_Export_*.xlsx",
        output_file=OUTPUT_FILE,
        script_path=Path(__file__),
        extra_deps=[SCRIPTS_DIR / "config" / "column_mappings.py"]
    )

    if cache.is_valid() and not args.force:
        print("Using cached output (source unchanged)")
        return True

    # ... process xlsx ...

    cache.save_metadata()
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CacheMetadata:
    """Metadata stored alongside cached output."""
    source_file: str          # Filename of the source xlsx
    source_mtime: float       # Modification time of source when processed
    source_size: int          # Size of source file in bytes
    deps_hash: str            # Hash of script + dependency files
    processed_at: str         # ISO timestamp when cache was created


def compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of a file's contents."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        # Read in chunks for memory efficiency
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_dependencies_hash(script_path: Path, extra_deps: Optional[list[Path]] = None) -> str:
    """
    Compute a combined hash of the script and its dependencies.
    
    This ensures the cache is invalidated when code changes, even if
    the source data file hasn't changed.
    """
    if extra_deps is None:
        extra_deps = []
    
    hasher = hashlib.md5()
    
    # Include script file
    all_deps = [script_path] + extra_deps
    
    for dep_path in sorted(all_deps):  # Sort for deterministic ordering
        if dep_path.exists():
            # Include path for identity + content for changes
            hasher.update(str(dep_path).encode())
            with open(dep_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
    
    return hasher.hexdigest()


def find_latest_xlsx(directory: Path, pattern: str) -> Optional[Path]:
    """
    Find the most recent xlsx file matching the pattern.
    
    Selection strategy:
    1. Primary: Most recent by modification time
    2. Tie-breaker: Lexicographically latest filename
    
    This ensures deterministic selection even with clock issues.
    """
    files = list(directory.glob(pattern))
    if not files:
        return None
    
    # Sort by (mtime descending, filename descending) for stable selection
    files.sort(key=lambda f: (f.stat().st_mtime, f.name), reverse=True)
    return files[0]


class XlsxCacheManager:
    """
    Manages caching for xlsx-to-csv pipeline stages.
    
    The cache uses:
    - The output CSV as the cached artifact (no separate cache file)
    - A metadata sidecar file (.meta.json) for validation
    """
    
    def __init__(
        self,
        source_dir: Path,
        source_pattern: str,
        output_file: Path,
        script_path: Path,
        extra_deps: Optional[list[Path]] = None
    ):
        """
        Initialize the cache manager.
        
        Args:
            source_dir: Directory containing source xlsx files
            source_pattern: Glob pattern for source files (e.g., "ProjectDashboard_Export_*.xlsx")
            output_file: Path to the output CSV (this IS the cache)
            script_path: Path to the script file (for code change detection)
            extra_deps: Additional dependency files (e.g., config modules)
        """
        self.source_dir = source_dir
        self.source_pattern = source_pattern
        self.output_file = output_file
        self.script_path = script_path
        self.extra_deps = extra_deps or []
        
        # Metadata file is stored alongside output
        self.meta_file = output_file.parent / f".{output_file.stem}.meta.json"
        
        # Compute current dependencies hash
        self.deps_hash = compute_dependencies_hash(script_path, self.extra_deps)
        
        # Find current source file
        self._source_file: Optional[Path] = None
    
    @property
    def source_file(self) -> Optional[Path]:
        """Get the current source file (cached after first lookup)."""
        if self._source_file is None:
            self._source_file = find_latest_xlsx(self.source_dir, self.source_pattern)
        return self._source_file
    
    def _load_metadata(self) -> Optional[CacheMetadata]:
        """Load metadata from sidecar file, returning None if invalid."""
        if not self.meta_file.exists():
            return None
        
        try:
            with open(self.meta_file, "r") as f:
                data = json.load(f)
            return CacheMetadata(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"  WARNING: Corrupted cache metadata, will rebuild: {e}")
            return None
    
    def is_valid(self) -> bool:
        """
        Check if the cache is valid and can be used.
        
        Returns True only if ALL of:
        1. Source xlsx file exists
        2. Output CSV exists
        3. Metadata sidecar exists and is valid
        4. Source filename matches (same file)
        5. Source mtime matches (not modified)
        6. Source size matches (not modified)
        7. Dependencies hash matches (code not changed)
        """
        # 1. Must have a source file
        if self.source_file is None:
            print("  Cache invalid: No source xlsx found")
            return False
        
        # 2. Output must exist
        if not self.output_file.exists():
            print("  Cache invalid: Output CSV does not exist")
            return False
        
        # 3. Metadata must exist and be valid
        meta = self._load_metadata()
        if meta is None:
            print("  Cache invalid: Metadata missing or corrupted")
            return False
        
        # 4. Same source file
        if meta.source_file != self.source_file.name:
            print(f"  Cache invalid: Source file changed ({meta.source_file} -> {self.source_file.name})")
            return False
        
        # 5-6. Source not modified (check both mtime and size)
        current_stat = self.source_file.stat()
        
        # Use != to catch both newer AND older files (e.g., restored backups)
        if current_stat.st_mtime != meta.source_mtime:
            print(f"  Cache invalid: Source mtime changed")
            return False
        
        if current_stat.st_size != meta.source_size:
            print(f"  Cache invalid: Source size changed")
            return False
        
        # 7. Code not changed
        if meta.deps_hash != self.deps_hash:
            print(f"  Cache invalid: Script or dependencies changed")
            return False
        
        return True
    
    def save_metadata(self) -> None:
        """Save metadata after successful processing."""
        if self.source_file is None:
            raise ValueError("Cannot save metadata: no source file")
        
        stat = self.source_file.stat()
        meta = CacheMetadata(
            source_file=self.source_file.name,
            source_mtime=stat.st_mtime,
            source_size=stat.st_size,
            deps_hash=self.deps_hash,
            processed_at=datetime.now().isoformat()
        )
        
        # Write to temp file then rename (atomic on POSIX)
        temp_file = self.meta_file.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(asdict(meta), f, indent=2)
        temp_file.rename(self.meta_file)
        
        print(f"  Saved cache metadata: {self.meta_file.name}")
    
    def get_cache_info(self) -> str:
        """Get human-readable cache status info."""
        if not self.output_file.exists():
            return "No cache (output missing)"
        
        meta = self._load_metadata()
        if meta is None:
            return "No cache (metadata missing)"
        
        return f"Cache from {meta.processed_at} (source: {meta.source_file})"


def atomic_write_csv(df, filepath: Path, **csv_kwargs) -> None:
    """
    Write DataFrame to CSV atomically.
    
    Writes to a temp file first, then renames to final path.
    This prevents partial/corrupt CSVs if the write is interrupted.
    
    Args:
        df: pandas DataFrame to write
        filepath: Final destination path
        **csv_kwargs: Arguments to pass to df.to_csv()
    """
    import os
    
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file in same directory (ensures same filesystem for atomic rename)
    temp_file = filepath.with_suffix(f".tmp.{os.getpid()}")
    
    try:
        df.to_csv(temp_file, **csv_kwargs)
        
        # Atomic rename (on POSIX systems)
        temp_file.rename(filepath)
    except Exception:
        # Clean up temp file on failure
        if temp_file.exists():
            temp_file.unlink()
        raise
