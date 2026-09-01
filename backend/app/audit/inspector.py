"""Secure ZIP extraction and passive project inspection module."""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Security & resource bounds
MAX_ZIP_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_EXTRACTED_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_FILE_COUNT = 10_000

LANGUAGE_EXTENSIONS: Dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hxx": "cpp",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
}

IGNORED_DIR_NAMES = {
    "__macosx",
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    ".vscode",
    ".idea",
    "node_modules",
    ".venv",
    "venv",
    ".pytest_cache",
}

IGNORED_FILENAMES = {
    ".ds_store",
    "thumbs.db",
}


class ZipExtractionError(Exception):
    """Base exception for zip extraction failures."""
    pass


class InvalidZipError(ZipExtractionError):
    """Raised when file is not a valid ZIP archive."""
    pass


class SizeLimitExceededError(ZipExtractionError):
    """Raised when ZIP or extracted contents exceed allowed size."""
    pass


class PathTraversalError(ZipExtractionError):
    """Raised when ZIP contains dangerous or path-traversing paths."""
    pass


class FileCountLimitError(ZipExtractionError):
    """Raised when ZIP contains too many files."""
    pass


class FileInfo(BaseModel):
    path: str
    extension: str
    size_bytes: int


class ProjectInspectionResponse(BaseModel):
    project_id: str
    filename: str
    file_count: int
    total_size_bytes: int
    languages: List[str]
    files: List[FileInfo]
    likely_source_files: List[str]


def inspect_and_extract_project_zip(
    zip_bytes: bytes,
    original_filename: str,
    target_base_dir: Optional[Path] = None,
) -> Tuple[ProjectInspectionResponse, Path]:
    """Securely validate, inspect, and extract a project ZIP archive without executing any code.

    Returns:
        (ProjectInspectionResponse, extracted_root_directory_path)
    """
    # 1. Validate ZIP binary size
    if len(zip_bytes) > MAX_ZIP_SIZE:
        raise SizeLimitExceededError(
            f"Uploaded ZIP size ({len(zip_bytes)} bytes) exceeds the maximum allowed {MAX_ZIP_SIZE} bytes (50 MB)."
        )

    if len(zip_bytes) == 0:
        raise InvalidZipError("Uploaded file is empty.")

    # 2. Validate ZIP format
    try:
        zip_buffer = io.BytesIO(zip_bytes)
        if not zipfile.is_zipfile(zip_buffer):
            raise InvalidZipError("Uploaded file is not a valid ZIP archive.")
        zf = zipfile.ZipFile(zip_buffer, "r")
    except Exception as exc:
        if isinstance(exc, ZipExtractionError):
            raise
        raise InvalidZipError(f"Failed to parse ZIP archive: {str(exc)}") from exc

    # 3. Security verification pass over ZipInfo metadata
    infolist = zf.infolist()
    if len(infolist) > MAX_FILE_COUNT:
        raise FileCountLimitError(
            f"ZIP contains {len(infolist)} entries, exceeding the maximum limit of {MAX_FILE_COUNT}."
        )

    total_uncompressed_size = 0
    clean_entries: List[zipfile.ZipInfo] = []

    for info in infolist:
        total_uncompressed_size += info.file_size
        if total_uncompressed_size > MAX_EXTRACTED_SIZE:
            raise SizeLimitExceededError(
                f"Extracted content size exceeds the maximum limit of {MAX_EXTRACTED_SIZE} bytes (200 MB)."
            )

        name = info.filename
        # Check for path traversal attempts
        if (
            name.startswith("/")
            or name.startswith("\\")
            or (len(name) >= 2 and name[1] == ":")  # Windows absolute drive like C:
            or ".." in name.replace("\\", "/").split("/")
        ):
            raise PathTraversalError(f"Dangerous path entry detected in ZIP: '{name}'. Path traversal rejected.")

        # Ignore macOS and metadata garbage
        parts = [p.lower() for p in name.replace("\\", "/").split("/") if p]
        if any(p in IGNORED_DIR_NAMES for p in parts[:-1]):
            continue
        if parts and parts[-1] in IGNORED_FILENAMES:
            continue

        clean_entries.append(info)

    # 4. Prepare target extraction workspace
    project_id = str(uuid.uuid4())
    if target_base_dir is None:
        target_base_dir = Path(tempfile.gettempdir()) / "autoverify_projects"
    
    project_extract_dir = target_base_dir / project_id
    project_extract_dir.mkdir(parents=True, exist_ok=True)
    target_root_resolved = project_extract_dir.resolve()

    try:
        # 5. Extract files safely one by one
        for info in clean_entries:
            # Re-verify resolved destination before writing
            dest_path = (project_extract_dir / info.filename).resolve()
            if not str(dest_path).startswith(str(target_root_resolved)):
                raise PathTraversalError(
                    f"Path escape attempt during extraction: '{info.filename}' resolves outside target directory."
                )

            if info.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src_file, open(dest_path, "wb") as dst_file:
                    shutil.copyfileobj(src_file, dst_file)

        # 6. Determine project root folder (flatten single wrapper directory if present)
        extracted_items = [
            p for p in project_extract_dir.iterdir()
            if p.name.lower() not in IGNORED_DIR_NAMES and p.name.lower() not in IGNORED_FILENAMES
        ]
        effective_root = project_extract_dir
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            effective_root = extracted_items[0]

        # 7. Passive inspection of extracted files
        file_infos: List[FileInfo] = []
        likely_source_files: List[str] = []
        detected_languages: Set[str] = set()
        total_size = 0

        for root, dirs, files in os.walk(effective_root):
            # Filter ignored directories in-place
            dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIR_NAMES]

            for fname in sorted(files):
                if fname.lower() in IGNORED_FILENAMES:
                    continue

                full_path = Path(root) / fname
                try:
                    rel_path = full_path.relative_to(effective_root).as_posix()
                    sz = full_path.stat().st_size
                except Exception:
                    continue

                ext = full_path.suffix.lower()
                total_size += sz

                file_infos.append(FileInfo(path=rel_path, extension=ext, size_bytes=sz))

                if ext in LANGUAGE_EXTENSIONS:
                    lang = LANGUAGE_EXTENSIONS[ext]
                    detected_languages.add(lang)
                    likely_source_files.append(rel_path)

        # Sort files and languages
        file_infos.sort(key=lambda f: f.path)
        likely_source_files.sort()
        sorted_languages = sorted(detected_languages)

        response = ProjectInspectionResponse(
            project_id=project_id,
            filename=original_filename,
            file_count=len(file_infos),
            total_size_bytes=total_size,
            languages=sorted_languages,
            files=file_infos,
            likely_source_files=likely_source_files,
        )
        return response, effective_root

    except Exception:
        # Clean up directory on failure
        if project_extract_dir.exists():
            shutil.rmtree(project_extract_dir, ignore_errors=True)
        raise
