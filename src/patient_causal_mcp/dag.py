"""Simple DAG representation and pragmatic adjustment-set checks."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from patient_causal_mcp.scenarios import Edge, get_scenario


def nodes_from_edges(edges: list[Edge]) -> list[str]:
    """Return sorted unique nodes from directed edges."""

    return sorted({node for edge in edges for node in edge})


def edges_to_dot(edges: list[Edge], graph_name: str = "PatientCausalDAG") -> str:
    """Serialize directed edges to Graphviz DOT."""

    lines = [f"digraph {graph_name} {{"]
    for source, target in edges:
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)


def edges_to_mermaid(edges: list[Edge]) -> str:
    """Serialize directed edges to Mermaid flowchart text."""

    lines = ["flowchart TD"]
    for source, target in edges:
        safe_source = source.replace("-", "_")
        safe_target = target.replace("-", "_")
        lines.append(f"  {safe_source}[{source}] --> {safe_target}[{target}]")
    return "\n".join(lines)


def ancestors_of(edges: list[Edge], node: str) -> set[str]:
    """Return all ancestors of a node."""

    parents: dict[str, list[str]] = defaultdict(list)
    for source, target in edges:
        parents[target].append(source)

    ancestors: set[str] = set()
    queue: deque[str] = deque(parents[node])
    while queue:
        current = queue.popleft()
        if current in ancestors:
            continue
        ancestors.add(current)
        queue.extend(parents[current])
    return ancestors


def descendants_of(edges: list[Edge], node: str) -> set[str]:
    """Return all descendants of a node."""

    children: dict[str, list[str]] = defaultdict(list)
    for source, target in edges:
        children[source].append(target)

    descendants: set[str] = set()
    queue: deque[str] = deque(children[node])
    while queue:
        current = queue.popleft()
        if current in descendants:
            continue
        descendants.add(current)
        queue.extend(children[current])
    return descendants


def identify_colliders(edges: list[Edge]) -> list[str]:
    """Identify nodes with two or more direct causes."""

    parents: dict[str, set[str]] = defaultdict(set)
    for source, target in edges:
        parents[target].add(source)
    return sorted(node for node, node_parents in parents.items() if len(node_parents) >= 2)


def generate_causal_dag(
    *,
    scenario: str,
    variables: list[str] | None = None,
) -> dict[str, Any]:
    """Return an interpretable DAG for a scenario."""

    scenario_def = get_scenario(scenario)
    edges = scenario_def.dag_edges
    if variables:
        variable_set = set(variables)
        variable_set.update({scenario_def.exposure, scenario_def.outcome})
        edges = [(source, target) for source, target in edges if source in variable_set and target in variable_set]

    return {
        "scenario": scenario_def.name,
        "nodes": nodes_from_edges(edges),
        "edges": [{"source": source, "target": target} for source, target in edges],
        "exposure": scenario_def.exposure,
        "outcome": scenario_def.outcome,
        "confounders": scenario_def.confounders,
        "mediators": scenario_def.mediators,
        "colliders": scenario_def.colliders or identify_colliders(edges),
        "adjustment_set": scenario_def.adjustment_set,
        "variables_not_to_adjust_for": scenario_def.variables_not_to_adjust_for,
        "dot": edges_to_dot(edges, graph_name=scenario_def.name),
        "mermaid": edges_to_mermaid(edges),
    }


def check_adjustment_set(
    *,
    dag_edges: list[dict[str, str]] | list[Edge],
    exposure: str,
    outcome: str,
    adjustment_variables: list[str],
) -> dict[str, Any]:
    """Perform practical checks for a proposed adjustment set.

    This is intentionally simpler than a full d-separation engine. It identifies likely
    common causes, descendant mediators, and direct colliders that are common sources of
    avoidable bias in clinical assistant workflows.
    """

    edges: list[Edge] = [
        (edge["source"], edge["target"]) if isinstance(edge, dict) else edge for edge in dag_edges
    ]
    nodes = set(nodes_from_edges(edges))
    if exposure not in nodes:
        raise ValueError(f"Exposure '{exposure}' does not appear in the DAG.")
    if outcome not in nodes:
        raise ValueError(f"Outcome '{outcome}' does not appear in the DAG.")

    exposure_ancestors = ancestors_of(edges, exposure)
    outcome_ancestors = ancestors_of(edges, outcome)
    likely_confounders = sorted((exposure_ancestors & outcome_ancestors) - {exposure, outcome})
    adjusted = set(adjustment_variables)
    missing = sorted(set(likely_confounders) - adjusted)
    included = sorted(set(likely_confounders) & adjusted)

    exposure_descendants = descendants_of(edges, exposure)
    outcome_ancestors_after_exposure = ancestors_of(edges, outcome)
    possible_mediators = sorted((exposure_descendants & outcome_ancestors_after_exposure) - {outcome})
    mediators_adjusted = sorted(set(possible_mediators) & adjusted)

    direct_colliders = identify_colliders(edges)
    colliders_adjusted = sorted(set(direct_colliders) & adjusted)

    is_reasonable = not missing and not mediators_adjusted and not colliders_adjusted
    explanation_parts: list[str] = []
    if included:
        explanation_parts.append(f"Included likely confounders: {', '.join(included)}.")
    if missing:
        explanation_parts.append(f"Missing likely confounders: {', '.join(missing)}.")
    if mediators_adjusted:
        explanation_parts.append(
            f"Potential mediators adjusted for: {', '.join(mediators_adjusted)}; this may block part of the causal effect."
        )
    if colliders_adjusted:
        explanation_parts.append(
            f"Potential colliders adjusted for: {', '.join(colliders_adjusted)}; this may open biasing paths."
        )
    if is_reasonable:
        explanation_parts.append(
            "The set is a reasonable practical adjustment set for this simplified DAG, assuming no unmeasured confounding."
        )

    return {
        "is_reasonable": bool(is_reasonable),
        "likely_confounders_included": included,
        "likely_confounders_missing": missing,
        "possible_mediators_adjusted_for": mediators_adjusted,
        "possible_colliders_adjusted_for": colliders_adjusted,
        "explanation": " ".join(explanation_parts),
    }
