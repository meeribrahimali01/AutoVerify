"""Static Project Analyzer using AI provider."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ai.models import ProjectAnalysis, ProjectAnalysisResponse
from app.ai.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.ai.provider import AIProvider, get_ai_provider

logger = logging.getLogger(__name__)

# Reading bounds for AI prompt context
MAX_PER_FILE_BYTES = 60 * 1024  # 60 KB max per file
MAX_TOTAL_PROMPT_BYTES = 300 * 1024  # 300 KB max source code sent to AI

RELEVANT_EXTENSIONS = {
    ".py", ".java", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hxx",
    ".js", ".mjs", ".ts", ".tsx", ".go", ".rs", ".md", ".txt", ".json"
}

IGNORED_DIRS = {
    "__pycache__", ".git", ".svn", ".hg", ".vscode", ".idea",
    "node_modules", ".venv", "venv", "dist", "build", "target",
    "bin", "obj", ".pytest_cache"
}


def build_project_context(
    project_dir: Path,
    manual_entry_point: Optional[str] = None
) -> Tuple[str, str, List[str]]:
    """Recursively collect project structure and relevant source code excerpts.

    Returns:
        (project_tree_str, source_contents_str, candidate_entry_points)
    """
    file_tree_lines: List[str] = []
    source_sections: List[str] = []
    candidate_entry_points: List[str] = []
    total_bytes_read = 0

    for root, dirs, files in os.walk(project_dir):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRS]

        for fname in sorted(files):
            full_path = Path(root) / fname
            try:
                rel_path = full_path.relative_to(project_dir).as_posix()
            except Exception:
                continue

            file_tree_lines.append(f"- {rel_path}")

            ext = full_path.suffix.lower()
            if ext in {".py", ".java", ".cpp", ".c", ".ts", ".js"}:
                candidate_entry_points.append(rel_path)

            if ext in RELEVANT_EXTENSIONS and total_bytes_read < MAX_TOTAL_PROMPT_BYTES:
                try:
                    file_size = full_path.stat().st_size
                    read_size = min(file_size, MAX_PER_FILE_BYTES)
                    
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read(read_size)
                    
                    total_bytes_read += len(content.encode("utf-8"))
                    
                    source_sections.append(
                        f"--- FILE: {rel_path} ---\n{content}\n"
                    )
                except Exception as exc:
                    logger.warning("Could not read file %s for AI context: %s", rel_path, exc)

    tree_str = "\n".join(file_tree_lines) if file_tree_lines else "(No files)"
    sources_str = "\n\n".join(source_sections) if source_sections else "(No readable source files)"

    # Prioritize standard entrypoint filenames
    entry_priority_names = {"main.py", "app.py", "run.py", "index.py", "main.js", "index.js", "Main.java", "__main__.py"}
    candidate_entry_points.sort(
        key=lambda p: (
            0 if Path(p).name.lower() in entry_priority_names else 1,
            p.count("/"),
            p.lower(),
        )
    )
    
    return tree_str, sources_str, candidate_entry_points


def analyze_student_project(
    project_id: str,
    project_dir: Path,
    manual_entry_point: Optional[str] = None,
    provider: Optional[AIProvider] = None,
) -> ProjectAnalysisResponse:
    """Perform static AI analysis on an extracted student project."""
    if not project_dir.exists() or not project_dir.is_dir():
        return ProjectAnalysisResponse(
            status="ERROR",
            project_id=project_id,
            error=f"Project directory for ID '{project_id}' not found or has expired.",
        )

    # 1. Extract context
    tree_str, sources_str, candidate_entries = build_project_context(
        project_dir=project_dir,
        manual_entry_point=manual_entry_point,
    )

    ai_prov = provider or get_ai_provider()
    
    # 2. Check if provider is configured
    if not ai_prov.is_configured():
        return ProjectAnalysisResponse(
            status="AI_NOT_CONFIGURED",
            project_id=project_id,
            candidate_entry_points=candidate_entries,
            message="AI analysis provider is not configured. Set AUTOVERIFY_AI_API_KEY to enable automated code adaptation.",
        )

    override_note = ""
    if manual_entry_point:
        override_note = f"TEACHER OVERRIDE: The teacher has designated '{manual_entry_point}' as the expected entry point."

    user_prompt = USER_PROMPT_TEMPLATE.format(
        project_tree=tree_str,
        file_contents=sources_str,
        manual_override_note=override_note,
    )

    # 3. Request structured JSON from AI provider
    try:
        raw_json = ai_prov.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except Exception as exc:
        logger.error("AI analysis generation failed: %s", exc)
        return ProjectAnalysisResponse(
            status="ERROR",
            project_id=project_id,
            candidate_entry_points=candidate_entries,
            error=f"AI provider analysis failed: {str(exc)}",
        )

    # 4. Parse and validate structured output via Pydantic
    try:
        # Sanitize / ensure required fields
        if not isinstance(raw_json, dict):
            raise ValueError("AI response did not return a valid JSON dictionary.")

        # Ensure language default
        raw_json.setdefault("language", "unknown")
        raw_json.setdefault("conversion_type", "epsilon_nfa_to_dfa")
        raw_json.setdefault("confidence", 0.5)

        analysis = ProjectAnalysis(**raw_json)
        
        # Override entry point if manual selection provided
        if manual_entry_point:
            analysis.entry_point = manual_entry_point

        # Status based on confidence and ambiguities
        status = "SUCCESS"
        if analysis.confidence < 0.65 or len(analysis.ambiguities) > 0 or not analysis.entry_point:
            status = "LOW_CONFIDENCE"

        return ProjectAnalysisResponse(
            status=status,
            project_id=project_id,
            analysis=analysis,
            candidate_entry_points=candidate_entries,
            message="Project analysis completed successfully.",
        )

    except Exception as exc:
        logger.error("Validation of AI analysis payload failed: %s", exc)
        return ProjectAnalysisResponse(
            status="ERROR",
            project_id=project_id,
            candidate_entry_points=candidate_entries,
            error=f"Malformed AI analysis output: {str(exc)}",
        )
