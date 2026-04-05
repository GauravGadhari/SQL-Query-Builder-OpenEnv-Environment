# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""SQL Query Builder Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import SqlQueryAction, SqlQueryObservation


class SqlQueryEnv(
    EnvClient[SqlQueryAction, SqlQueryObservation, State]
):
    """
    Client for the SQL Query Builder Environment.

    Maintains a persistent WebSocket connection to the environment server.

    Example:
        >>> with SqlQueryEnv(base_url="http://localhost:8000").sync() as client:
        ...     result = client.reset(options={"task": "simple_lookup"})
        ...     print(result.observation.question)
        ...     result = client.step(SqlQueryAction(query="SELECT * FROM employees"))
        ...     print(result.reward)
    """

    def _step_payload(self, action: SqlQueryAction) -> Dict:
        """Convert SqlQueryAction to JSON payload for step message."""
        return {"query": action.query}

    def _parse_result(self, payload: Dict) -> StepResult[SqlQueryObservation]:
        """Parse server response into StepResult[SqlQueryObservation]."""
        obs_data = payload.get("observation", {})
        observation = SqlQueryObservation(
            done=payload.get("done", False),
            reward=payload.get("reward"),
            db_schema=obs_data.get("db_schema", ""),
            question=obs_data.get("question", ""),
            task_name=obs_data.get("task_name", ""),
            task_difficulty=obs_data.get("task_difficulty", ""),
            hints=obs_data.get("hints", []),
            agent_result=obs_data.get("agent_result", []),
            expected_result=obs_data.get("expected_result", []),
            feedback=obs_data.get("feedback", ""),
            reward_breakdown=obs_data.get("reward_breakdown", {}),
            error=obs_data.get("error"),
            attempts_remaining=obs_data.get("attempts_remaining", 0),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State object."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
