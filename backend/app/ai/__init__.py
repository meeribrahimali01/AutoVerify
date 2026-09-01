"""AI-assisted static code analysis package."""

from app.ai.analyzer import analyze_student_project
from app.ai.models import ProjectAnalysis, ProjectAnalysisRequest, ProjectAnalysisResponse
from app.ai.provider import AIProvider, GeminiProvider, MockAIProvider, get_ai_provider, set_ai_provider

__all__ = [
    "analyze_student_project",
    "ProjectAnalysis",
    "ProjectAnalysisRequest",
    "ProjectAnalysisResponse",
    "AIProvider",
    "GeminiProvider",
    "MockAIProvider",
    "get_ai_provider",
    "set_ai_provider",
]
