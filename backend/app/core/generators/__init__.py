"""Test-suite generation package."""

from app.core.generators.edge_cases import (
    GeneratedTestCase,
    TestCaseMetadata,
    compute_metadata,
    edge_case_dead_states,
    edge_case_dense_epsilon_clique,
    edge_case_empty_language,
    edge_case_epsilon_cycle,
    edge_case_epsilon_only_acceptance,
    edge_case_single_state_accepting,
    edge_case_single_state_rejecting,
    edge_case_universal_language,
    edge_case_unreachable_states,
    get_all_edge_cases,
)
from app.core.generators.random_nfa import (
    ALL_CATEGORIES,
    GeneratorConfig,
    generate_epsilon_nfa,
    generate_test_suite,
)

__all__ = [
    "ALL_CATEGORIES",
    "GeneratorConfig",
    "GeneratedTestCase",
    "TestCaseMetadata",
    "compute_metadata",
    "generate_epsilon_nfa",
    "generate_test_suite",
    "get_all_edge_cases",
    "edge_case_empty_language",
    "edge_case_universal_language",
    "edge_case_single_state_rejecting",
    "edge_case_single_state_accepting",
    "edge_case_epsilon_only_acceptance",
    "edge_case_epsilon_cycle",
    "edge_case_unreachable_states",
    "edge_case_dead_states",
    "edge_case_dense_epsilon_clique",
]
