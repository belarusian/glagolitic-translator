"""Live integration test runner against local llama.cpp models.

Usage:
    python examples/run_live.py --variant toolcall --prompt "..."
    python examples/run_live.py --variant responses --prompt "..."
    python examples/run_live.py --variant mini --prompt "..."

Variants:
    toolcall    Chat Completions API + tool calls
    responses   Responses API + tool calls (equivalent to mini-swe-agent)
    mini        mini-swe-agent subprocess

Environment variables:
    FIVE_BASE_URL    Endpoint URL (default: http://192.168.1.157:8080/v1)
    FIVE_MODEL       Model ID (default: fast-qwen)
    FIVE_MAX_TOKENS  Max tokens per response (default: 1024)
    FIVE_MAX_STEPS   Max loop steps (default: 10)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from five.core import run, Ok, Err, save_trajectory
from five.env import local_env, local_env_response, format_fix


def make_parser():
    p = argparse.ArgumentParser(description="Run Five live test")
    p.add_argument(
        "--variant",
        choices=["toolcall", "responses", "mini"],
        default="toolcall",
    )
    p.add_argument(
        "--endpoint",
        default=os.getenv("FIVE_BASE_URL", "http://192.168.1.157:8080/v1"),
    )
    p.add_argument("--prompt", default=None)
    return p


def run_five_variant(variant, endpoint, prompt, model_id, max_tokens, max_steps):
    """Run one of the Five variants (toolcall, responses)."""
    step_num = [0]
    debug_g: Callable = lambda m: Err("not configured")  # type: ignore
    v1 = None
    system = None

    if variant == "toolcall":
        from five.model import litellm_toolcall_invoke
        from five.parse import toolcall_parse

        LITELLM_MODEL = f"openai/{model_id}"

        def debug_g(messages):
            step_num[0] += 1
            t0 = time.time()
            result = litellm_toolcall_invoke(
                model=LITELLM_MODEL,
                base_url=endpoint,
                temperature=0.3,
                max_tokens=max_tokens,
                api_key="dummy",
            )(messages)
            elapsed = time.time() - t0
            if isinstance(result, Ok):
                preview = result.value[:120].replace("\n", " ")
                print(f"  [G step {step_num[0]}] ({elapsed:.1f}s) -> {preview}...")
            else:
                print(f"  [G step {step_num[0]}] ({elapsed:.1f}s) ERR: {result.error[:100]}")
            return result

        v1 = toolcall_parse()
        system = "You are a helpful assistant that can interact with a computer."

    elif variant == "responses":
        from five.model import http_response_invoke
        from five.parse import toolcall_response_parse

        def debug_g(messages):
            step_num[0] += 1
            t0 = time.time()
            result = http_response_invoke(
                base_url=endpoint,
                model=model_id,
                api_key="dummy",
                max_output_tokens=max_tokens,
            )(messages)
            elapsed = time.time() - t0
            if isinstance(result, Ok):
                preview = result.value[:120].replace("\n", " ")
                print(f"  [G step {step_num[0]}] ({elapsed:.1f}s) -> {preview}...")
            else:
                print(f"  [G step {step_num[0]}] ({elapsed:.1f}s) ERR: {result.error[:100]}")
            return result

        v1 = toolcall_response_parse()
        system = (
            "You are a bash agent. You solve tasks by executing bash commands. "
            "When the task is fully done, run: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
        )

    assert debug_g is not None and v1 is not None and system is not None

    v2 = local_env() if variant != "responses" else local_env_response()

    # Derive a clean log filename from the endpoint
    clean = endpoint.replace("http://", "").replace("https://", "").rstrip("/")
    if clean.endswith("/v1"):
        clean = clean[:-3]
    clean = clean.replace(":", "_")
    log_file = os.path.join(os.path.dirname(__file__), f"log_{clean}_{variant}.json")

    def emit(messages, outcome):
        p = Path(log_file)
        with open(p, "w") as f:
            json.dump({"outcome": outcome, "messages": messages}, f, indent=2)
        return p

    print(f"Variant: {variant}")
    print(f"Endpoint: {endpoint}")
    print(f"Prompt: {prompt[:120]}")
    print("-" * 60)

    path = run(
        G=debug_g,
        V1=v1,
        V2=v2,
        G_prime=format_fix,
        emit=emit,
        system=system,
        prompt=prompt,
        max_steps=max_steps,
    )

    print(f"\nTrajectory saved to: {log_file}")
    print(f"Total G calls: {step_num[0]}")
    return path


def run_mini_agent(endpoint, prompt, model_id):
    """Run mini-swe-agent as a subprocess."""
    log_file = os.path.join(os.path.dirname(__file__), f"log_mini_{model_id}.json")

    mini_repo = os.path.expandvars("/Users/av4nda/Research/mini-swe-agent")
    config_path = os.path.expandvars(
        "/Users/av4nda/Library/Application Support/mini-swe-agent/config.yaml"
    )

    env = os.environ.copy()
    env["MSWEA_MODEL_NAME"] = f"openai/{model_id}"
    env["MSWEA_CONFIGURED"] = "1"
    env["OPENAI_BASE_URL"] = endpoint

    cmd = [
        "mini",
        "-c", os.path.join(mini_repo, "src/minisweagent/config/mini.yaml"),
        "-c", config_path,
        "-t", prompt,
        "-o", log_file,
        "-y",
        "--exit-immediately",
    ]

    print(f"Variant: mini-swe-agent")
    print(f"Endpoint: {endpoint}")
    print(f"Prompt: {prompt[:120]}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=mini_repo, env=env)

    print(f"\nTrajectory saved to: {log_file}")
    print(f"Exit code: {result.returncode}")
    return Path(log_file)


def main():
    args = make_parser().parse_args()

    MODEL_ID = os.getenv("FIVE_MODEL", "fast-qwen")
    BASE_URL = args.endpoint
    MAX_TOKENS = int(os.getenv("FIVE_MAX_TOKENS", "1024"))
    MAX_STEPS = int(os.getenv("FIVE_MAX_STEPS", "10"))

    prompt = args.prompt or (
        "List all .py files in /Users/av4nda/Research/glagolitic-translator/src/five, "
        "then count lines in the largest one. Show the final count."
    )

    if args.variant == "mini":
        run_mini_agent(BASE_URL, prompt, MODEL_ID)
    else:
        run_five_variant(
            args.variant, BASE_URL, prompt, MODEL_ID, MAX_TOKENS, MAX_STEPS
        )


if __name__ == "__main__":
    main()
