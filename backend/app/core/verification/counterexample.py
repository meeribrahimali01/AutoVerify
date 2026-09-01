"""Counterexample reconstruction from BFS exploration tree."""

from __future__ import annotations

from typing import Dict, List, Tuple
from app.core.verification.product import ProductState


def reconstruct_counterexample(
    mismatch_state: ProductState,
    start_state: ProductState,
    predecessors: Dict[ProductState, Tuple[ProductState, str]],
) -> Tuple[str, List[dict]]:
    """Reconstruct the shortest distinguishing string from BFS predecessor map.

    Args:
        mismatch_state: The reachable product state where acceptance differs.
        start_state: The initial product state (A.start_state, B.start_state).
        predecessors: Mapping from child product state -> (parent product state, symbol).

    Returns:
        Tuple[str, List[dict]]: The reconstructed counterexample string and trace path.
    """
    if mismatch_state == start_state:
        return "", []

    symbols_rev: list[str] = []
    path_rev: list[dict] = []
    curr = mismatch_state

    while curr != start_state:
        parent, sym = predecessors[curr]
        symbols_rev.append(sym)
        path_rev.append({
            "from_state": (parent.state_a, parent.state_b),
            "symbol": sym,
            "to_state": (curr.state_a, curr.state_b),
        })
        curr = parent

    # Reverse to obtain chronological path
    symbols_rev.reverse()
    path_rev.reverse()

    return "".join(symbols_rev), path_rev
