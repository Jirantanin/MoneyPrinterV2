#!/usr/bin/env python3
"""Kill any process on port 8899 then start the Studio."""
import os
import shutil
import subprocess

PORT = int(os.environ.get("PODCAST_STUDIO_PORT") or os.environ.get("PORT") or "8899")
ROOT = os.path.dirname(os.path.abspath(__file__))


def _candidate_main_root() -> str:
    parent = os.path.dirname(ROOT)
    return os.path.join(parent, "MoneyPrinterV2")


def _resolve_venv_python() -> str:
    candidates = [
        os.environ.get("MONEYPRINTER_VENV_PY", ""),
        os.path.join(ROOT, "venv", "Scripts", "python.exe"),
        os.path.join(ROOT, ".venv", "Scripts", "python.exe"),
        os.path.join(_candidate_main_root(), "venv", "Scripts", "python.exe"),
        os.path.join(_candidate_main_root(), ".venv", "Scripts", "python.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "No Python virtualenv found. Expected one of: "
        + ", ".join(path for path in candidates if path)
    )


VENV_PY = _resolve_venv_python()


def ensure_config() -> None:
    config_path = os.path.join(ROOT, "config.json")
    if os.path.exists(config_path):
        return
    candidates = [
        os.environ.get("MONEYPRINTER_CONFIG_JSON", ""),
        os.path.join(_candidate_main_root(), "config.json"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            shutil.copy2(candidate, config_path)
            print(f"[restart] Copied config.json from {candidate}")
            return
    raise FileNotFoundError(
        "config.json not found in this worktree and no reusable config was found. "
        "Copy config.json from the main MoneyPrinterV2 checkout or set MONEYPRINTER_CONFIG_JSON."
    )


def kill_port(port: int) -> None:
    result = subprocess.run(["netstat", "-aon"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if f":{port} " in line or f":{port}\t" in line:
            parts = line.split()
            pid = parts[-1]
            if pid.isdigit() and pid != "0":
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                print(f"[restart] Killed PID {pid} on port {port}")
                return
    print(f"[restart] No process on port {port}")


def main() -> None:
    kill_port(PORT)
    ensure_config()
    print("[restart] Starting Studio...")
    print(f"[restart] Python: {VENV_PY}")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(ROOT, "src")
    env["PODCAST_STUDIO_PORT"] = str(PORT)
    env.setdefault("PYTHONUTF8", "1")
    subprocess.run(
        [VENV_PY, "-c",
         "from podcast_server import launch_podcast_server; launch_podcast_server()"],
        cwd=ROOT,
        env=env,
    )


if __name__ == "__main__":
    main()
