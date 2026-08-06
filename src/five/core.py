"""Five-function algebra for agents.

invoke   : G   -- messages → Result[raw]
parse    : V1  -- raw → Result[action]
validate : V2  -- action → Result[observation | Exit]
fix      : G'  -- (error, messages) → message | None
emit     : IO  -- (messages, outcome) → Path

The loop: (G → V1 → [V2, V2, ...])* → emit

Format errors are appended as user messages — no inner retry loop.
Consecutive format errors are tracked and abort after N failures.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar, TypeAlias, Union

from tenacity import Retrying, retry_if_not_exception_type, stop_after_attempt, wait_exponential

T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Ok(Generic[T]):
    value: T


@dataclass
class Err(Generic[E]):
    error: E


Result: TypeAlias = Union[Ok[T], Err[E]]


# ── Retry wrapper ───────────────────────────────────────────────────────────

logger = logging.getLogger("five.model")


class AbortError(Exception):
    """Error that should not be retried."""
    pass


def retry_invoke(
    invoke_fn: "Invoke",
    *,
    max_attempts: int | None = None,
) -> "Invoke":
    """Wrap an Invoke function with tenacity retry logic.

    Retries on transient errors (rate limits, timeouts, server errors).
    Does NOT retry on abort errors (invalid API key, auth errors, etc).
    """
    if max_attempts is None:
        max_attempts = int(os.getenv("FIVE_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))

    abort_types = (AbortError,)
    retrying = Retrying(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_not_exception_type(abort_types),
    )

    def _invoke(messages: list[dict]) -> Ok[str] | Err[str]:
        def _call() -> Ok[str] | Err[str]:
            result = invoke_fn(messages)
            if isinstance(result, Err):
                error = result.error.lower()
                # Abort on auth/permission errors
                if any(kw in error for kw in ("invalidapi", "permission", "unauthorized", "forbidden")):
                    raise AbortError(result.error)
                # Retry on transient errors
                if any(kw in error for kw in ("rate_limit", "timeout", "too many", "server error", "overloaded")):
                    raise RuntimeError(result.error)
            return result

        try:
            return retrying(_call)
        except AbortError as e:
            return Err(f"abort: {e}")
        except Exception as e:
            return Err(f"retry_exhausted: {e}")

    return _invoke


# ── Signatures ──────────────────────────────────────────────────────────────

Invoke = Callable[[list[dict]], Result[str, str]]
Parse = Callable[[str], Result[list[dict] | str, str]]
Validate = Callable[[str], Result[dict, str]]
Fix = Callable[[str, list[dict]], dict | None]
Emit = Callable[[list[dict], str], Path]


# ── The loop ────────────────────────────────────────────────────────────────

def run(
    G: Invoke,
    V1: Parse,
    V2: Validate,
    G_prime: Fix | None,
    emit: Emit,
    system: str,
    prompt: str,
    max_steps: int = 100,
) -> Path:
    """Five-function evaluator.

    Loop: (G → V1 → [V2, V2, ...])* → emit

    G  → query LLM, get raw text
    V1 → extract bash action(s) from text (returns list of {command, tool_call_id} or plain string)
    [G'] → on V1 failure: format error as retry message (optional)
    V2 → execute each action, get observation with tool_call_id correlation
    emit → save trajectory
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    for step in range(max_steps):
        # G: invoke
        raw = G(messages)
        if isinstance(raw, Err):
            return emit(messages, f"model_error: {raw.error}")

        # V1: parse — returns Ok(list[dict]) or Ok(str) or Err
        actions = V1(raw.value)
        if isinstance(actions, Err):
            fix = G_prime(actions.error, messages) if G_prime else None
            if fix:
                messages.append(fix)
                continue
            return emit(messages, f"format_error: {actions.error}")

        # V2: validate / execute each action with tool_call_id correlation
        action_list = actions.value if isinstance(actions.value, list) else [actions.value]

        for action in action_list:
            command = action["command"] if isinstance(action, dict) else action
            tool_call_id = action.get("tool_call_id") if isinstance(action, dict) else None

            result = V2(command)
            if isinstance(result, Err):
                return emit(messages, result.error)

            observation = result.value
            if tool_call_id:
                observation["tool_call_id"] = tool_call_id
            messages.append(observation)

    return emit(messages, "max_steps_reached")


# ── Trajectory I/O ─────────────────────────────────────────────────────────


def save_trajectory(
    output_dir: Path | str = "trajectories",
) -> Emit:
    """Return an emit function that saves trajectories as JSON."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    def _emit(messages: list[dict], outcome: str) -> Path:
        idx = len(list(out.glob("*.json")))
        path = out / f"trajectory_{idx:04d}.json"
        path.write_text(
            json.dumps({"outcome": outcome, "messages": messages}, indent=2)
        )
        return path

    return _emit
