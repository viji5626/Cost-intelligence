"""
Tool Circuit Breaker & Loop Protection Engine (AI-11)
Prevents infinite agentic recursion, duplicate tool invocation loops, and total execution budget overruns.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class ToolCircuitBreaker:
    """
    Stateful circuit breaker tracking tool call history per task.
    """

    def __init__(
        self,
        max_calls_per_step: int = 3,
        max_iterations: int = 3,
        max_total_calls_per_task: int = 10,
        max_total_runtime_seconds: float = 15.0,
    ):
        self.max_calls_per_step = max_calls_per_step
        self.max_iterations = max_iterations
        self.max_total_calls_per_task = max_total_calls_per_task
        self.max_total_runtime_seconds = max_total_runtime_seconds

        # Task tracking: task_id -> list of (tool_name, args_hash, timestamp, duration)
        self._task_invocations: Dict[str, List[Tuple[str, str, float, float]]] = {}
        # Task iteration counter: task_id -> current iteration count
        self._task_iterations: Dict[str, int] = {}
        # Task step call counter: task_id -> current step call count
        self._task_step_calls: Dict[str, int] = {}

    @staticmethod
    def compute_arguments_hash(arguments: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 hash of normalized JSON arguments."""
        try:
            encoded = json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
            return hashlib.sha256(encoded).hexdigest()
        except Exception:
            return hashlib.sha256(str(arguments).encode("utf-8")).hexdigest()

    def advance_iteration(self, task_id: str) -> None:
        """Advances the iteration step counter and resets per-step call count."""
        self._task_iterations[task_id] = self._task_iterations.get(task_id, 0) + 1
        self._task_step_calls[task_id] = 0

    def check_invocation_allowed(
        self,
        task_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates whether the requested tool invocation complies with loop and budget rules.
        Returns: (is_allowed, denial_reason)
        """
        args_hash = self.compute_arguments_hash(arguments)
        invocations = self._task_invocations.get(task_id, [])

        # 1. Total Calls per Task Budget
        if len(invocations) >= self.max_total_calls_per_task:
            return False, f"Total task tool call budget exceeded ({len(invocations)} >= {self.max_total_calls_per_task})."

        # 2. Total Cumulative Runtime Budget
        total_runtime = sum(inv[3] for inv in invocations)
        if total_runtime >= self.max_total_runtime_seconds:
            return False, f"Total cumulative tool runtime exceeded ({total_runtime:.2f}s >= {self.max_total_runtime_seconds:.1f}s)."

        # 3. Iteration Budget
        current_iteration = self._task_iterations.get(task_id, 1)
        if current_iteration > self.max_iterations:
            return False, f"Max retrieval/tool iterations exceeded ({current_iteration} > {self.max_iterations})."

        # 4. Calls Per Step Budget
        current_step_calls = self._task_step_calls.get(task_id, 0)
        if current_step_calls >= self.max_calls_per_step:
            return False, f"Max tool calls per step exceeded ({current_step_calls} >= {self.max_calls_per_step})."

        # 5. Duplicate Invocation Detection
        # Check if the exact same tool with identical arguments was called consecutively or more than twice in the task
        duplicate_count = sum(1 for inv in invocations if inv[0] == tool_name and inv[1] == args_hash)
        if duplicate_count >= 2:
            return False, f"Duplicate tool invocation loop detected for '{tool_name}' with identical arguments."

        if invocations and invocations[-1][0] == tool_name and invocations[-1][1] == args_hash:
            return False, f"Immediate consecutive duplicate call detected for '{tool_name}' with identical arguments."

        return True, None

    def record_invocation(
        self,
        task_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """Records a completed tool execution into the task history."""
        args_hash = self.compute_arguments_hash(arguments)
        if task_id not in self._task_invocations:
            self._task_invocations[task_id] = []
            self._task_iterations[task_id] = 1
            self._task_step_calls[task_id] = 0

        self._task_invocations[task_id].append(
            (tool_name, args_hash, time.time(), duration_seconds)
        )
        self._task_step_calls[task_id] = self._task_step_calls.get(task_id, 0) + 1

    def reset_task(self, task_id: str) -> None:
        """Clears execution history for a task."""
        self._task_invocations.pop(task_id, None)
        self._task_iterations.pop(task_id, None)
        self._task_step_calls.pop(task_id, None)
