"""Sets up isolated Codex CLI ("lead coding tool") homes for the two arms.

Arm A (no_mcp) and Arm B (with_mcp) are two separate `CODEX_HOME` directories,
each with their own auth and MCP registration, so the *only* difference
between what the agent can do in each arm is whether the `contextai-graph`
MCP server is registered. Sandbox policy, approval settings, and the model
are otherwise identical between arms (see codex_runner.py).

Important gotcha (found and fixed empirically): the contextai-graph MCP
server must NOT be spawned with its cwd inside a target repo. Several target
repos ship a module that shadows a stdlib name (e.g. flask/src/flask/typing.py
shadows `typing`), which breaks the server's own imports via Python's
`-m`-adds-cwd-to-sys.path behavior. We pin the server's cwd to this eval/
directory instead, which never has such a collision.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODEX_HOME_ROOT = HERE / "_codex_home"
NO_MCP_HOME = CODEX_HOME_ROOT / "no_mcp"
WITH_MCP_HOME = CODEX_HOME_ROOT / "with_mcp"

# Extra PATH entries for tools installed outside the default PATH in this env.
EXTRA_PATH = "/home/ubuntu/.npm-global/bin:/home/ubuntu/.local/bin"

MCP_SERVER_CWD = HERE


def subprocess_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{EXTRA_PATH}:{env.get('PATH', '')}"
    return env


def codex_home_for(arm: str) -> Path:
    if arm not in ("A", "B"):
        raise ValueError(f"arm must be 'A' or 'B', got {arm!r}")
    return WITH_MCP_HOME if arm == "B" else NO_MCP_HOME


def _login(home: Path, api_key: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    if (home / "auth.json").exists():
        return
    env = subprocess_env()
    env["CODEX_HOME"] = str(home)
    subprocess.run(
        ["codex", "login", "--with-api-key"],
        input=api_key,
        text=True,
        check=True,
        env=env,
        capture_output=True,
    )


def _register_mcp_server(home: Path) -> None:
    config_path = home / "config.toml"
    text = config_path.read_text() if config_path.exists() else ""
    if "contextai-graph" in text:
        return
    block = (
        '[mcp_servers.contextai-graph]\n'
        'command = "python3"\n'
        'args = ["-m", "contextai_mcp"]\n'
        f'cwd = "{MCP_SERVER_CWD}"\n'
    )
    with config_path.open("a") as f:
        f.write(block)


def ensure_setup() -> None:
    """Idempotent: creates both CODEX_HOMEs, logs each in, and registers the
    contextai-graph MCP server only in the 'with_mcp' (Arm B) home."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
    CODEX_HOME_ROOT.mkdir(parents=True, exist_ok=True)
    _login(NO_MCP_HOME, api_key)
    _login(WITH_MCP_HOME, api_key)
    _register_mcp_server(WITH_MCP_HOME)


if __name__ == "__main__":
    ensure_setup()
    print("no_mcp home:  ", NO_MCP_HOME)
    print("with_mcp home:", WITH_MCP_HOME)
    print((WITH_MCP_HOME / "config.toml").read_text())
