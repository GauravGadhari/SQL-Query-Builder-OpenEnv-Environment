# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
5-signal SQL grader for the SQL Query Builder Environment.

Scoring breakdown (weights sum to 1.0):
  - syntax_valid   (0.10) — Does the SQL parse?
  - executes       (0.15) — Does it run without errors?
  - correct_columns(0.15) — Are the column names correct?
  - correct_rows   (0.25) — Is the row count correct?
  - values_match   (0.35) — Do the actual values match?
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Tuple

import sqlparse


# ── Weight configuration ──────────────────────────────────
WEIGHTS: Dict[str, float] = {
    "syntax_valid": 0.10,
    "executes": 0.15,
    "correct_columns": 0.15,
    "correct_rows": 0.25,
    "values_match": 0.35,
}


def grade_query(
    conn: sqlite3.Connection,
    agent_sql: str,
    expected_sql: str,
) -> Dict[str, Any]:
    """Grade an agent's SQL query against the expected reference query.

    Args:
        conn: Active SQLite connection with the seeded database.
        agent_sql: The SQL query submitted by the agent.
        expected_sql: The reference SQL query that produces correct results.

    Returns:
        Dictionary with keys: reward, breakdown, error, agent_result, expected_result
    """
    breakdown: Dict[str, float] = {k: 0.0 for k in WEIGHTS}
    error: str | None = None
    agent_result: List[Dict[str, Any]] = []
    expected_result: List[Dict[str, Any]] = []

    # Always compute expected result first (we need it for comparison)
    try:
        expected_result = _execute_query(conn, expected_sql)
    except Exception as e:
        # If our own reference SQL fails, that's a bug — give full credit
        return _build_result(
            breakdown={k: 1.0 for k in WEIGHTS},
            error=f"Reference SQL error (env bug): {e}",
            agent_result=[],
            expected_result=[],
        )

    # ── Signal 1: Syntax valid (10%) ──
    agent_sql_stripped = agent_sql.strip().rstrip(";").strip()
    if not agent_sql_stripped:
        return _build_result(
            breakdown=breakdown,
            error="Empty query submitted",
            agent_result=[],
            expected_result=expected_result,
        )

    try:
        parsed = sqlparse.parse(agent_sql_stripped)
        if parsed and len(parsed) > 0 and parsed[0].tokens:
            breakdown["syntax_valid"] = 1.0
    except Exception:
        return _build_result(
            breakdown=breakdown,
            error="SQL syntax is invalid",
            agent_result=[],
            expected_result=expected_result,
        )

    # ── Signal 2: Executes without error (15%) ──
    try:
        agent_result = _execute_query(conn, agent_sql_stripped)
        breakdown["executes"] = 1.0
    except Exception as e:
        error = str(e)
        return _build_result(
            breakdown=breakdown,
            error=error,
            agent_result=[],
            expected_result=expected_result,
        )

    # ── Signal 3: Correct columns (15%) ──
    breakdown["correct_columns"] = _score_columns(agent_result, expected_result)

    # ── Signal 4: Correct row count (25%) ──
    breakdown["correct_rows"] = _score_row_count(agent_result, expected_result)

    # ── Signal 5: Values match (35%) ──
    breakdown["values_match"] = _score_values(agent_result, expected_result)

    return _build_result(
        breakdown=breakdown,
        error=error,
        agent_result=agent_result,
        expected_result=expected_result,
    )


# ── Helper functions ──────────────────────────────────────


def _execute_query(conn: sqlite3.Connection, sql: str) -> List[Dict[str, Any]]:
    """Execute SQL and return results as list of dicts."""
    cursor = conn.execute(sql)
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def _score_columns(
    agent: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> float:
    """Score column name overlap between agent and expected results."""
    if not expected:
        return 1.0 if not agent else 0.0
    if not agent:
        return 0.0

    agent_cols = set(k.lower() for k in agent[0].keys())
    expected_cols = set(k.lower() for k in expected[0].keys())

    if not expected_cols:
        return 1.0

    overlap = len(agent_cols & expected_cols)
    return round(overlap / len(expected_cols), 2)


def _score_row_count(
    agent: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> float:
    """Score how close the row counts are."""
    if not expected:
        return 1.0 if not agent else 0.0
    if not agent:
        return 0.0

    ratio = min(len(agent), len(expected)) / max(len(agent), len(expected))
    return round(ratio, 2)


def _score_values(
    agent: List[Dict[str, Any]], expected: List[Dict[str, Any]]
) -> float:
    """Score value overlap between agent and expected rows (order-insensitive)."""
    if not expected:
        return 1.0 if not agent else 0.0
    if not agent:
        return 0.0

    def normalize_row(row: Dict[str, Any]) -> Tuple:
        """Convert a row to a comparable tuple, normalizing all values to strings."""
        values = []
        for v in row.values():
            if v is None:
                values.append("__none__")
            elif isinstance(v, float):
                values.append(str(round(v, 2)))
            else:
                values.append(str(v).lower().strip())
        return tuple(sorted(values))

    agent_set = set(normalize_row(r) for r in agent)
    expected_set = set(normalize_row(r) for r in expected)

    if not expected_set:
        return 1.0

    matches = len(agent_set & expected_set)
    return round(matches / len(expected_set), 2)


def _build_result(
    breakdown: Dict[str, float],
    error: str | None,
    agent_result: List[Dict[str, Any]],
    expected_result: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute weighted reward from breakdown dict.

    The final reward is clamped to the open interval (0, 1) — strictly
    greater than 0.0 and strictly less than 1.0 — to satisfy the
    hackathon Phase 2 validator requirement.
    """
    reward = sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS)
    # Clamp to (0, 1) exclusive — validator rejects exactly 0.0 and 1.0
    reward = max(0.01, min(round(reward, 2), 0.99))
    return {
        "reward": reward,
        "breakdown": breakdown,
        "error": error,
        "agent_result": agent_result,
        "expected_result": expected_result,
    }
