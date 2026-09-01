"""Database ORM models for saved automata and audit runs.

Implementation to be added in future steps.
"""
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class SavedAutomaton(Base):
    __tablename__ = "saved_automata"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    automaton_type = Column(String(20), nullable=False)  # DFA, NFA, EPSILON_NFA
    data = Column(Text, nullable=False)  # JSON representation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
