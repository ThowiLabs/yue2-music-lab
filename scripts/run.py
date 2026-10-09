"""Ejecuta YuE2 en puertos exclusivos, sin afectar otros procesos."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def backend_config(port: int) -> dict:
    root = ROOT.resolve()
    return {
        "host": "127.0.0.1", "port": port, "backend": "cuda",
        "device": 0, "threads": 8, "lazy_load": True,
        "max_loaded_models": 1, "idle_unload_ms": 900000,
        "log_request_body": False, "max_request_body_bytes": 1048576,
        "models": [{
            "id": "yue2-q8", "family": "yue2",
            "path": str(root / "models/Yue2-3B-GGUF"),
            "model_spec_override": str(root / "engine/prebuilt/v0.9.0/model_specs/yue2.json"),
            "task": "gen", "mode": "offline",
            "session_options": {
                "yue2.model_gguf": "yue2-3b-q8_0.gguf",
                "yue2.vae_gguf": "yue2-vae-f16.gguf",
            },
        }],
    }


def port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def running_backend(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/v1/models", timeout=2
        ) as response:
            models = json.load(response)
        return any(m.get("id") == "yue2-q8" for m in models.get("data", []))
    except (OSError, ValueError):
        return False


def run() -> int:
    gradio_port = int(os.getenv("GRADIO_SERVER_PORT", "7875"))
    backend_port = int(os.getenv("YUE2_BACKEND_PORT", "7876"))
    if not (1024 <= gradio_port <= 65535 and 1024 <= backend_port <= 65535 and gradio_port != backend_port):
        raise SystemExit("Puertos no válidos o duplicados")
    if not port_free(gradio_port):
        raise SystemExit(f"El puerto Gradio {gradio_port} está ocupado; no se interfiere.")
    binary = ROOT / "engine/prebuilt/v0.9.0/audiocpp_server"
    if not binary.is_file():
        raise SystemExit("Falta audio.cpp; ejecuta python scripts/install.py")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = (
        "/usr/local/nvidia/lib64:/usr/local/cuda/lib64:"
        + env.get("LD_LIBRARY_PATH", "")
    ).rstrip(":")
    env["YUE2_API_URL"] = f"http://127.0.0.1:{backend_port}"
    child = None
    log_handle = None
    if running_backend(backend_port):
        print("Reutilizando API YuE2 ya disponible", flush=True)
    elif not port_free(backend_port):
        raise SystemExit(f"El puerto {backend_port} está ocupado por otro servicio.")
    else:
        config_path = ROOT / "server.json"
        config_path.write_text(json.dumps(backend_config(backend_port), indent=2), encoding="utf-8")
        log_path = ROOT / "logs"
        log_path.mkdir(exist_ok=True)
        log_handle = (log_path / "backend.log").open("a", encoding="utf-8")
        child = subprocess.Popen(
            [str(binary), "--config", str(config_path), "--no-ui", "--log"],
            cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
        )
        for _ in range(100):
            if running_backend(backend_port):
                break
            if child.poll() is not None:
                raise RuntimeError("Motor finalizó antes de iniciar: revisa logs/backend.log")
            time.sleep(0.2)
        else:
            raise RuntimeError("No respondió el motor CUDA: revisa logs/backend.log")
    try:
        return subprocess.call([sys.executable, "-u", str(ROOT / "app.py")], cwd=ROOT, env=env)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        if log_handle:
            log_handle.close()


if __name__ == "__main__":
    raise SystemExit(run())
