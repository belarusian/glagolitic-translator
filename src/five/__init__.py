"""Five-function algebra for agents.

Five functions compose. The loop is the evaluator.

invoke   : G   -- messages → Result[raw]
parse    : V1  -- raw → Result[action]
validate : V2  -- action → Result[observation | Exit]
fix      : G'  -- (error, messages) → message | None
emit     : IO  -- (messages, outcome) → Path
"""

from .core import Err, Ok, Result, run, save_trajectory
from .model import (
    BASH_TOOL,
    BASH_TOOL_RESPONSE_API,
    litellm_invoke,
    litellm_toolcall_invoke,
    litellm_response_invoke,
    http_response_invoke,
)
from .parse import regex_parse, toolcall_parse, toolcall_response_parse
from .env import format_fix, local_env, local_env_response

__all__ = [
    "Err",
    "Ok",
    "Result",
    "run",
    "save_trajectory",
    "BASH_TOOL",
    "BASH_TOOL_RESPONSE_API",
    "litellm_invoke",
    "litellm_toolcall_invoke",
    "litellm_response_invoke",
    "http_response_invoke",
    "regex_parse",
    "toolcall_parse",
    "toolcall_response_parse",
    "local_env",
    "local_env_response",
    "format_fix",
]
