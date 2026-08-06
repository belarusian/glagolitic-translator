"""Action parsers — implement V1 (parse)."""

from __future__ import annotations

import json
import re

from .core import Err, Ok, Parse


def regex_parse(
    pattern: str | None = None,
    error_template: str = "Found {count} actions. Expected exactly 1.",
) -> Parse:
    """Parse a single bash command from markdown code blocks.

    Accepts ```mswea_bash_command, ```bash, or ```sh blocks (in that priority order).
    """
    if pattern is None:
        # Try multiple block types in order of specificity
        patterns = [
            r"```mswea_bash_command\s*\n(.*?)\n```",
            r"```bash\s*\n(.*?)\n```",
            r"```sh\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",  # fallback: any code block
        ]
    else:
        patterns = [pattern]

    def _parse(raw: str) -> Ok[str] | Err[str]:
        for p in patterns:
            matches = re.findall(p, raw, re.DOTALL)
            if matches:
                # Return the first match from the most specific pattern that worked
                return Ok(matches[0].strip())
        # No code block found — model returned plain text = final answer
        return Err("exit:task_complete")

    return _parse


def toolcall_parse() -> Parse:
    """Parse tool-calling JSON into a bash command.

    Expects JSON array of {tool_call_id, name, arguments} where
    arguments is a JSON string with a 'command' field.

    Embeds tool_call_id as a comment prefix for V2 to extract.
    """

    def _parse(raw: str) -> Ok[str] | Err[str]:
        try:
            actions = json.loads(raw)
        except json.JSONDecodeError:
            # Not tool-call JSON — model returned plain text = final answer
            return Err("exit:task_complete")

        if not isinstance(actions, list) or not actions:
            return Err("No tool calls found")

        # Take the first bash tool call
        for action in actions:
            if action.get("name") == "bash":
                try:
                    args = json.loads(action["arguments"])
                    command = args["command"]
                    call_id = action.get("tool_call_id", "")
                    # Embed call_id as comment for V2 to extract
                    if call_id:
                        return Ok(f"#call_id:{call_id}\n{command}")
                    return Ok(command)
                except (json.JSONDecodeError, KeyError) as e:
                    return Err(f"Invalid bash tool call: {e}")

        return Err("No bash tool call found")

    return _parse


def toolcall_response_parse() -> Parse:
    """Parse JSON from Responses API function_call items.

    Same shape as toolcall_parse — the difference is in G, not V1.
    """
    return toolcall_parse()
