# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
SQL Query Builder — Core Environment Implementation.

Presents SQL tasks to an AI agent and grades its SQL query submissions
using a 5-signal reward function against a fresh SQLite database.
"""

from __future__ import annotations

import random
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import SqlQueryAction, SqlQueryObservation
except (ImportError, ModuleNotFoundError):
    from models import SqlQueryAction, SqlQueryObservation

try:
    from .database import create_database, get_schema_text
    from .grader import grade_query
    from .tasks import TASKS
except (ImportError, ModuleNotFoundError):
    from server.database import create_database, get_schema_text
    from server.grader import grade_query
    from server.tasks import TASKS


MAX_ATTEMPTS = 5  # Agent gets 5 tries per question


class SqlQueryEnvironment(Environment):
    """SQL Query Builder Environment.

    On reset(), creates a fresh SQLite database and selects a question
    from the requested task tier. On step(), grades the agent's SQL query
    against the reference answer using a 5-signal reward function.

    Supports concurrent WebSocket sessions (each gets its own instance).
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._conn = None
        self._current_task = None
        self._current_question = None
        self._best_reward = 0.0

    # ──────────────────────────────────────────────
    # reset()
    # ──────────────────────────────────────────────
    def reset(self, *, seed: int | None = None, options: dict | None = None) -> SqlQueryObservation:
        """Reset the environment for a new episode.

        Args:
            seed: Optional random seed for reproducibility.
            options: Optional dict. Supports:
                - task (str): Task name to use. Random if not provided.

        Returns:
            Initial observation with database schema and question.
        """
        if seed is not None:
            random.seed(seed)

        opts = options or {}
        task_name = opts.get("task") or random.choice(list(TASKS.keys()))

        if task_name not in TASKS:
            task_name = random.choice(list(TASKS.keys()))

        task_data = TASKS[task_name]
        question = random.choice(task_data["questions"])

        # Fresh database for every episode
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = create_database()
        self._current_task = task_data
        self._current_question = question
        self._best_reward = 0.0

        self._state = State(
            episode_id=str(uuid4()),
            step_count=0,
        )

        return SqlQueryObservation(
            done=False,
            reward=0.0,
            db_schema=get_schema_text(),
            question=question["question"],
            task_name=task_name,
            task_difficulty=task_data["difficulty"],
            hints=question.get("hints", []),
            feedback=f"Write a SQL query to answer the question. You have {MAX_ATTEMPTS} attempts.",
            attempts_remaining=MAX_ATTEMPTS,
        )

    # ──────────────────────────────────────────────
    # step()
    # ──────────────────────────────────────────────
    def step(self, action: SqlQueryAction) -> SqlQueryObservation:
        """Execute a step: grade the agent's SQL query.

        Args:
            action: SqlQueryAction containing the SQL query string.

        Returns:
            Observation with grading results, feedback, and reward.
        """
        self._state.step_count += 1

        # Grade the query
        result = grade_query(
            self._conn,
            action.query,
            self._current_question["expected_sql"],
        )

        reward = result["reward"]
        self._best_reward = max(self._best_reward, reward)

        # Check episode termination
        perfect = reward >= 0.99
        out_of_attempts = self._state.step_count >= MAX_ATTEMPTS
        done = perfect or out_of_attempts

        # Build human-readable feedback
        feedback = self._build_feedback(reward, perfect, out_of_attempts, result)
        remaining = MAX_ATTEMPTS - self._state.step_count
        # Always include expected result so inference debug logs can show diffs
        # (the LLM agent only receives the feedback text, not raw observation fields)
        return SqlQueryObservation(
            done=done,
            reward=reward,
            db_schema=get_schema_text(),
            question=self._current_question["question"],
            task_name=list(TASKS.keys())[
                list(TASKS.values()).index(self._current_task)
            ],
            task_difficulty=self._current_task["difficulty"],
            hints=self._current_question.get("hints", []),
            agent_result=result["agent_result"][:20],
            expected_result=result["expected_result"][:20],
            feedback=feedback,
            reward_breakdown=result["breakdown"],
            error=result["error"],
            attempts_remaining=max(0, remaining),
        )

    # ──────────────────────────────────────────────
    # state
    # ──────────────────────────────────────────────
    @property
    def state(self) -> State:
        """Return current episode state."""
        return self._state

    # ──────────────────────────────────────────────
    # helpers
    # ──────────────────────────────────────────────
    def _build_feedback(
        self,
        reward: float,
        perfect: bool,
        out_of_attempts: bool,
        result: dict,
    ) -> str:
        """Build a human-readable feedback string."""
        if perfect:
            return "Perfect! Your query produces the correct result."

        parts = [f"Score: {reward:.2f}/1.00."]

        if result.get("error"):
            parts.append(f"Error: {result['error']}")
        else:
            bd = result["breakdown"]
            agent_rows = result.get("agent_result", [])
            expected_rows = result.get("expected_result", [])

            if bd.get("correct_columns", 0) < 1.0:
                # Tell the agent exactly which columns are expected vs what it gave
                expected_cols = sorted(expected_rows[0].keys()) if expected_rows else []
                agent_cols = sorted(agent_rows[0].keys()) if agent_rows else []
                missing = set(expected_cols) - set(agent_cols)
                extra = set(agent_cols) - set(expected_cols)
                msg = "Column mismatch."
                if missing:
                    msg += f" Expected columns not found: {', '.join(sorted(missing))}."
                if extra:
                    msg += f" Unexpected columns: {', '.join(sorted(extra))}."
                if expected_cols:
                    msg += f" Expected columns: {', '.join(expected_cols)}."
                parts.append(msg)

            if bd.get("correct_rows", 0) < 1.0:
                parts.append(
                    f"Row count mismatch: your query returned {len(agent_rows)} rows, "
                    f"expected {len(expected_rows)}."
                )

            if bd.get("values_match", 0) < 1.0 and bd.get("correct_rows", 0) >= 0.5:
                match_pct = int(bd["values_match"] * 100)
                parts.append(
                    f"Value mismatch: only {match_pct}% of rows match the expected result. "
                    "Check your WHERE/JOIN conditions and sort order."
                )

        if out_of_attempts:
            parts.append(f"Out of attempts. Best score: {self._best_reward:.2f}")
        else:
            remaining = MAX_ATTEMPTS - self._state.step_count
            parts.append(f"{remaining} attempt(s) remaining.")

        return " ".join(parts)

