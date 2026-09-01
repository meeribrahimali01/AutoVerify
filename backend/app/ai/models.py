"""Pydantic schemas for AI-assisted project analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProjectAnalysis(BaseModel):
    """Structured static analysis of student automata project codebase."""
    language: str = Field("unknown", description="Programming language: python, java, cpp, c, javascript, typescript, etc.")
    entry_point: Optional[str] = Field(None, description="Primary entry point filename relative to project root")
    relevant_files: List[str] = Field(default_factory=list, description="Relevant source files analyzed")
    converter_file: Optional[str] = Field(None, description="Filename containing the primary conversion logic")
    converter_function: Optional[str] = Field(None, description="Function name implementing conversion (if applicable)")
    converter_class: Optional[str] = Field(None, description="Class name implementing conversion (if applicable)")
    input_format: str = Field("json", description="Expected input format: json, stdin_json, cli_args, custom_txt")
    output_format: str = Field("json", description="Expected output format: json, stdout_json, custom_txt")
    invocation: Optional[str] = Field(None, description="Command line template to execute, e.g. 'python main.py <input.json>'")
    conversion_type: str = Field("epsilon_nfa_to_dfa", description="Identified transformation: epsilon_nfa_to_dfa, nfa_to_dfa, etc.")
    is_supported_language: bool = Field(True, description="Whether an execution runtime adapter is supported (Python, Java, C, C++)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    ambiguities: List[str] = Field(default_factory=list, description="Ambiguities or alternative entry points identified")
    reasoning_summary: str = Field("", description="Short justification explaining how the interface was inferred")


class ProjectAnalysisRequest(BaseModel):
    """Request payload to analyze an uploaded project."""
    project_id: str = Field(..., description="ID of previously extracted project")
    manual_entry_point: Optional[str] = Field(None, description="Optional teacher-specified entry point override")


class ProjectAnalysisResponse(BaseModel):
    """Response returned by the /analyze-project endpoint."""
    status: str = Field("SUCCESS", description="SUCCESS | AI_NOT_CONFIGURED | LOW_CONFIDENCE | ERROR")
    project_id: str
    analysis: Optional[ProjectAnalysis] = None
    candidate_entry_points: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    error: Optional[str] = None
