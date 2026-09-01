"""Base transformation interfaces for finite automata."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from app.core.automata.models import BaseAutomaton

InputAutomaton = TypeVar("InputAutomaton", bound=BaseAutomaton)
OutputAutomaton = TypeVar("OutputAutomaton", bound=BaseAutomaton)


class BaseTransformation(ABC, Generic[InputAutomaton, OutputAutomaton]):
    """Abstract base class for automata transformations."""

    @abstractmethod
    def transform(self, automaton: InputAutomaton) -> OutputAutomaton:
        """Transform an input automaton to target automaton representation."""
        pass
