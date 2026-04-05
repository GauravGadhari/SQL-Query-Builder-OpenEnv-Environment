# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the SQL Query Builder Environment.

This environment trains AI agents to write SQL queries against a realistic
database schema. Actions are SQL query strings; observations include the
database schema, natural-language questions, query results, and detailed
grading feedback.
"""

from typing import Any, Dict, List, Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class SqlQueryAction(Action):
    """Agent submits a SQL query to answer the posed question."""

    query: str = Field(..., description="SQL query string to execute against the database")


class SqlQueryObservation(Observation):
    """Observation returned to the agent after reset() or step()."""

    # --- Problem description (always present) ---
    db_schema: str = Field(default="", description="Database schema as CREATE TABLE statements")
    question: str = Field(default="", description="Natural-language question to answer with SQL")
    task_name: str = Field(default="", description="Task identifier: simple_lookup | analytics_query | complex_report")
    task_difficulty: str = Field(default="", description="Difficulty level: easy | medium | hard")
    hints: List[str] = Field(default_factory=list, description="Optional hints for the agent")

    # --- Grading feedback (after step()) ---
    agent_result: List[Dict[str, Any]] = Field(default_factory=list, description="Rows returned by agent's SQL query")
    expected_result: List[Dict[str, Any]] = Field(default_factory=list, description="Rows returned by the reference SQL query")
    feedback: str = Field(default="", description="Human-readable grading feedback")
    reward_breakdown: Dict[str, float] = Field(default_factory=dict, description="Per-signal reward breakdown")
    error: Optional[str] = Field(default=None, description="SQL error message if query failed")

    # --- Episode control ---
    attempts_remaining: int = Field(default=3, description="Number of remaining attempts")
