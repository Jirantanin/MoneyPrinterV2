#!/usr/bin/env python3
"""Kill any process on port 8899 then start the Studio."""
import os
import subprocess

PORT = 8899
ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, "venv", "Scripts", "python.exe")


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
    print("[restart] Starting Studio...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(ROOT, "src")
    subprocess.run(
        [VENV_PY, "-c",
         "from podcast_server import launch_podcast_server; launch_podcast_server()"],
        cwd=ROOT,
        env=env,
    )


if __name__ == "__main__":
    main()
