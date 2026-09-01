"""Configurable, category-driven automated test-suite generator for ε-NFAs."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence

from app.core.automata.models import EPSILON, EpsilonNFA
from app.core.generators.edge_cases import (
    GeneratedTestCase,
    compute_metadata,
    get_all_edge_cases,
)

ALL_CATEGORIES: List[str] = [
    "A_BASIC",
    "B_EPSILON_HEAVY",
    "C_ACCEPTANCE_SENSITIVE",
    "D_MULTIPLE_ACCEPTING",
    "E_CYCLIC",
    "F_SPARSE",
    "G_DENSE",
    "H_UNREACHABLE_STATES",
    "I_DEAD_STATES",
    "J_MIXED_RANDOM",
]


@dataclass
class GeneratorConfig:
    """Configuration for automated test suite generation."""

    min_states: int = 1
    max_states: int = 6
    alphabet: Sequence[str] = ("0", "1")
    transition_density: float = 0.35
    epsilon_probability: float = 0.25
    accepting_probability: float = 0.35
    categories: Sequence[str] | None = None
    count: int = 20

    def __post_init__(self) -> None:
        if self.min_states < 1:
            raise ValueError("min_states must be >= 1")
        if self.max_states < self.min_states:
            raise ValueError("max_states must be >= min_states")
        if not self.alphabet:
            raise ValueError("alphabet cannot be empty")
        if EPSILON in self.alphabet:
            raise ValueError("alphabet must not contain epsilon symbol")


# ============================================================================
# CATEGORY-SPECIFIC GENERATORS
# ============================================================================


def _generate_basic(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category A: Simple transitions."""
    n_states = rng.randint(config.min_states, min(config.max_states, max(config.min_states, 2)))
    states = {f"q{i}" for i in range(n_states)}
    start_state = "q0"
    num_acc = rng.randint(0, n_states)
    accepting_states = set(rng.sample(sorted(states), num_acc)) if num_acc else set()

    transitions: dict[tuple[str, str], set[str]] = {}
    for s in states:
        for sym in config.alphabet:
            if rng.random() < 0.5:
                dest = rng.choice(sorted(states))
                transitions.setdefault((s, sym), set()).add(dest)
        if rng.random() < 0.2:  # Occasional epsilon
            dest = rng.choice(sorted(states))
            transitions.setdefault((s, EPSILON), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "A_BASIC", seed=seed, description="Small basic automaton")
    return GeneratedTestCase(enfa, meta)


def _generate_epsilon_heavy(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category B: Heavy epsilon usage (chains, branching, cycles)."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_states = {sorted_states[-1]}

    transitions: dict[tuple[str, str], set[str]] = {}

    # Guaranteed epsilon chain q0 -> q1 -> ... -> q(n-1)
    for i in range(n_states - 1):
        transitions.setdefault((sorted_states[i], EPSILON), set()).add(sorted_states[i + 1])

    # Add extra epsilon branching and cycles
    for s in states:
        for _ in range(rng.randint(1, 2)):
            dest = rng.choice(sorted_states)
            transitions.setdefault((s, EPSILON), set()).add(dest)
        # Few normal transitions
        for sym in config.alphabet:
            if rng.random() < 0.25:
                dest = rng.choice(sorted_states)
                transitions.setdefault((s, sym), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "B_EPSILON_HEAVY", seed=seed, description="Epsilon-heavy with chains and cycles")
    return GeneratedTestCase(enfa, meta)


def _generate_acceptance_sensitive(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category C: Epsilon closure directly controls string acceptance."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_states = {sorted_states[min(1, n_states - 1)], sorted_states[-1]}

    transitions: dict[tuple[str, str], set[str]] = {}
    if n_states > 1:
        # Epsilon branch from start state to accepting state
        transitions.setdefault((start_state, EPSILON), set()).add(sorted_states[1])

    for s in states:
        for sym in config.alphabet:
            if rng.random() < 0.35:
                dest = rng.choice(sorted_states)
                transitions.setdefault((s, sym), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "C_ACCEPTANCE_SENSITIVE", seed=seed, description="Epsilon path directly controls acceptance")
    return GeneratedTestCase(enfa, meta)


def _generate_multiple_accepting(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category D: Multiple accepting states."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    num_acc = rng.randint(min(2, n_states), n_states)
    accepting_states = set(rng.sample(sorted_states, num_acc))

    transitions: dict[tuple[str, str], set[str]] = {}
    for s in states:
        for sym in list(config.alphabet) + [EPSILON]:
            if rng.random() < 0.3:
                dest = rng.choice(sorted_states)
                transitions.setdefault((s, sym), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "D_MULTIPLE_ACCEPTING", seed=seed, description="Multiple distinct accepting states")
    return GeneratedTestCase(enfa, meta)


def _generate_cyclic(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category E: Directed cycles of symbols and epsilons."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_states = {sorted_states[-1]}

    transitions: dict[tuple[str, str], set[str]] = {}
    # Explicit loop q0 -> q1 -> ... -> q(n-1) -> q0
    for i in range(n_states):
        src = sorted_states[i]
        dst = sorted_states[(i + 1) % n_states]
        sym = rng.choice(list(config.alphabet) + [EPSILON])
        transitions.setdefault((src, sym), set()).add(dst)

    # Extra random transitions
    for s in states:
        for sym in list(config.alphabet) + [EPSILON]:
            if rng.random() < 0.2:
                dest = rng.choice(sorted_states)
                transitions.setdefault((s, sym), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "E_CYCLIC", seed=seed, description="Directed cycles across states")
    return GeneratedTestCase(enfa, meta)


def _generate_sparse(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category F: Low transition density."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_states = {rng.choice(sorted_states)}

    transitions: dict[tuple[str, str], set[str]] = {}
    # Sparse: at most 1 transition per state
    for s in states:
        if rng.random() < 0.6:
            sym = rng.choice(list(config.alphabet) + [EPSILON])
            dest = rng.choice(sorted_states)
            transitions[(s, sym)] = {dest}

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "F_SPARSE", seed=seed, description="Sparse transition topology")
    return GeneratedTestCase(enfa, meta)


def _generate_dense(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category G: High transition density."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_states = set(rng.sample(sorted_states, rng.randint(1, n_states)))

    transitions: dict[tuple[str, str], set[str]] = {}
    for s in states:
        for sym in list(config.alphabet) + [EPSILON]:
            if rng.random() < 0.7:
                num_dests = rng.randint(1, min(2, n_states))
                dests = set(rng.sample(sorted_states, num_dests))
                transitions[(s, sym)] = dests

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "G_DENSE", seed=seed, description="Dense multi-destination transitions")
    return GeneratedTestCase(enfa, meta)


def _generate_unreachable(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category H: Guaranteed unreachable states."""
    n_states = max(3, rng.randint(config.min_states, config.max_states))
    reachable = {f"q{i}" for i in range(n_states - 1)}
    unreachable = {f"q{n_states - 1}"}
    states = reachable | unreachable
    start_state = "q0"
    accepting_states = set(rng.sample(sorted(states), 1))

    transitions: dict[tuple[str, str], set[str]] = {}
    for s in reachable:
        for sym in list(config.alphabet) + [EPSILON]:
            if rng.random() < 0.35:
                dest = rng.choice(sorted(reachable))
                transitions.setdefault((s, sym), set()).add(dest)

    for u in unreachable:
        dest = rng.choice(sorted(states))
        transitions.setdefault((u, rng.choice(list(config.alphabet))), set()).add(dest)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "H_UNREACHABLE_STATES", seed=seed, description="Contains unreachable isolated states")
    return GeneratedTestCase(enfa, meta)


def _generate_dead_states(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category I: Reachable dead/sink states that cannot reach accepting states."""
    n_states = max(3, rng.randint(config.min_states, config.max_states))
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"
    accepting_state = sorted_states[1]
    sink_state = sorted_states[-1]

    transitions: dict[tuple[str, str], set[str]] = {
        (start_state, config.alphabet[0]): {accepting_state},
        (start_state, config.alphabet[-1]): {sink_state},
    }
    for sym in config.alphabet:
        transitions.setdefault((sink_state, sym), set()).add(sink_state)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states={accepting_state},
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "I_DEAD_STATES", seed=seed, description="Contains reachable non-accepting sink state")
    return GeneratedTestCase(enfa, meta)


def _generate_mixed_random(config: GeneratorConfig, rng: random.Random, test_id: str, seed: int | None = None) -> GeneratedTestCase:
    """Category J: Parameterized general random generation."""
    n_states = rng.randint(config.min_states, config.max_states)
    states = {f"q{i}" for i in range(n_states)}
    sorted_states = sorted(states)
    start_state = "q0"

    num_acc = sum(1 for _ in states if rng.random() < config.accepting_probability)
    accepting_states = set(rng.sample(sorted_states, num_acc)) if num_acc else {rng.choice(sorted_states)}

    transitions: dict[tuple[str, str], set[str]] = {}
    for s in states:
        for sym in config.alphabet:
            if rng.random() < config.transition_density:
                num_dst = rng.randint(1, min(2, n_states))
                dsts = set(rng.sample(sorted_states, num_dst))
                transitions.setdefault((s, sym), set()).update(dsts)
        if rng.random() < config.epsilon_probability:
            num_dst = rng.randint(1, min(2, n_states))
            dsts = set(rng.sample(sorted_states, num_dst))
            transitions.setdefault((s, EPSILON), set()).update(dsts)

    enfa = EpsilonNFA(
        states=states,
        alphabet=config.alphabet,
        start_state=start_state,
        accepting_states=accepting_states,
        transitions=transitions,
    )
    meta = compute_metadata(enfa, test_id, "J_MIXED_RANDOM", seed=seed, description="Mixed randomized configuration")
    return GeneratedTestCase(enfa, meta)


CATEGORY_DISPATCH = {
    "A_BASIC": _generate_basic,
    "B_EPSILON_HEAVY": _generate_epsilon_heavy,
    "C_ACCEPTANCE_SENSITIVE": _generate_acceptance_sensitive,
    "D_MULTIPLE_ACCEPTING": _generate_multiple_accepting,
    "E_CYCLIC": _generate_cyclic,
    "F_SPARSE": _generate_sparse,
    "G_DENSE": _generate_dense,
    "H_UNREACHABLE_STATES": _generate_unreachable,
    "I_DEAD_STATES": _generate_dead_states,
    "J_MIXED_RANDOM": _generate_mixed_random,
}


def generate_epsilon_nfa(
    config: GeneratorConfig | None = None,
    category: str = "J_MIXED_RANDOM",
    rng: random.Random | None = None,
    test_id: str = "gen_0",
    seed: int | None = None,
) -> GeneratedTestCase:
    """Generate a single valid EpsilonNFA according to config and category."""
    cfg = config or GeneratorConfig()
    generator_fn = CATEGORY_DISPATCH.get(category, _generate_mixed_random)
    active_rng = rng if rng is not None else random.Random(seed)
    return generator_fn(cfg, active_rng, test_id, seed=seed)


def generate_test_suite(
    config: GeneratorConfig | None = None,
    seed: int | None = 42,
    include_edge_cases: bool = True,
) -> List[GeneratedTestCase]:
    """Generate a complete, deterministic suite of diverse ε-NFA test cases.

    Args:
        config: Optional GeneratorConfig parameters.
        seed: Random seed for reproducible generation.
        include_edge_cases: If True, prepends deterministic boundary edge cases.

    Returns:
        List[GeneratedTestCase]: List of valid test cases with metadata.
    """
    cfg = config or GeneratorConfig()
    rng = random.Random(seed)
    suite: list[GeneratedTestCase] = []

    # 1. Include deterministic edge cases if requested
    if include_edge_cases:
        suite.extend(get_all_edge_cases())

    # 2. Distribute requested count across enabled categories
    categories = cfg.categories or ALL_CATEGORIES
    remaining_count = max(1, cfg.count)

    for i in range(remaining_count):
        cat = categories[i % len(categories)]
        test_id = f"test_{cat.lower()}_{i+1}"
        case = generate_epsilon_nfa(config=cfg, category=cat, rng=rng, test_id=test_id, seed=seed)
        suite.append(case)

    return suite
