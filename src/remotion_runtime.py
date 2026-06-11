"""Helpers for invoking the local Remotion toolchain on Windows reliably."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


_WINDOWS_NODE_CANDIDATES = [
    r"C:\Program Files\nodejs\node.exe",
    r"C:\Program Files\Microsoft Visual Studio\18\Professional\MSBuild\Microsoft\VisualStudio\NodeJs\node.exe",
    r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Microsoft\VisualStudio\NodeJs\node.exe",
    r"C:\Program Files\nodejsx\node.exe",
]


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for raw_path in paths:
        if not raw_path:
            continue
        path = str(Path(raw_path).expanduser())
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _node_is_usable(path: str) -> bool:
    candidate = Path(path)
    if not candidate.is_file():
        return False
    try:
        subprocess.run(
            [str(candidate), "-e", "process.exit(0)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def resolve_node_executable() -> str:
    """Return a Node executable that can actually be launched."""

    candidates = [
        os.environ.get("REMOTION_NODE_PATH", ""),
        os.environ.get("NODE_BINARY", ""),
        os.environ.get("NODE_EXE", ""),
        *_WINDOWS_NODE_CANDIDATES,
        shutil.which("node") or "",
    ]
    for path in _dedupe(candidates):
        if _node_is_usable(path):
            return str(Path(path).resolve())

    raise FileNotFoundError(
        "No runnable Node.js executable found. Install Node.js or set REMOTION_NODE_PATH "
        "to a working node.exe before rendering."
    )


def remotion_subprocess_env(node_executable: str | None = None) -> dict[str, str]:
    """Build an env where child scripts resolve the same usable Node first."""

    node_path = Path(node_executable or resolve_node_executable()).resolve()
    env = os.environ.copy()
    env["PATH"] = str(node_path.parent) + os.pathsep + env.get("PATH", "")
    env.setdefault("REMOTION_NODE_PATH", str(node_path))
    return env


def remotion_cli_command(remotion_dir: Path, *args: str) -> list[str]:
    """Build a direct local Remotion CLI command without depending on npx."""

    node_executable = resolve_node_executable()
    cli_path = remotion_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if not cli_path.is_file():
        raise FileNotFoundError(
            f"Local Remotion CLI not found at {cli_path}. Run npm install in {remotion_dir}."
        )
    return [node_executable, str(cli_path), *args]
