"""Inicia Gradio y un worker nativo audio.cpp por GPU CUDA disponible."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def backend_config(port: int, device: int = 0) -> dict:
    root = ROOT.resolve()
    return {
        "host": "127.0.0.1",
        "port": port,
        "backend": "cuda",
        "device": device,
        "threads": max(4, min(8, os.cpu_count() or 4)),
        "lazy_load": True,
        "max_loaded_models": 1,
        "idle_unload_ms": 900000,
        "log_request_body": False,
        "max_request_body_bytes": 1048576,
        "models": [{
            "id": "yue2-q8",
            "family": "yue2",
            "path": str(root / "models/Yue2-3B-GGUF"),
            "model_spec_override": str(root / "engine/prebuilt/v0.9.0/model_specs/yue2.json"),
            "task": "gen",
            "mode": "offline",
            "session_options": {
                "yue2.model_gguf": "yue2-3b-q8_0.gguf",
                "yue2.vae_gguf": "yue2-vae-f16.gguf",
            },
        }],
    }


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def model_entry(port: int) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as response:
            models = json.load(response)
        return next((item for item in models.get("data", []) if item.get("id") == "yue2-q8"), None)
    except (OSError, ValueError, AttributeError):
        return None


def running_backend(port: int) -> bool:
    return model_entry(port) is not None


def available_cuda_devices(binary: Path, env: dict[str, str]) -> list[int]:
    """Lee el orden real de dispositivos CUDA usado por audio.cpp."""
    result = subprocess.run(
        [str(binary), "--list-devices"],
        capture_output=True, text=True, env=env, timeout=20, check=False,
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    devices = []
    for line in output.splitlines():
        match = re.search(r"\bDevice\s+(\d+)\s*:\s*(.+)", line, flags=re.IGNORECASE)
        if match and "CPU" not in match.group(2).upper():
            devices.append(int(match.group(1)))
    if devices:
        return sorted(set(devices))
    count = re.search(r"found\s+(\d+)\s+CUDA devices", output, flags=re.IGNORECASE)
    if count and int(count.group(1)) > 0:
        return list(range(int(count.group(1))))
    raise RuntimeError("audio.cpp no detectó dispositivos CUDA. Comprueba nvidia-smi y los drivers.")


def wait_for_backend(port: int, child: subprocess.Popen, seconds: float = 18) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if running_backend(port):
            return True
        if child.poll() is not None:
            return False
        time.sleep(0.25)
    return running_backend(port)


def stop_child(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def gpu_plan(devices: list[int], mode: str = "auto") -> tuple[list[int], list[int], bool]:
    """Elige entre baja latencia Multi-GPU y varias generaciones independientes."""
    normalized = mode.strip().lower()
    if normalized not in {"auto", "on", "true", "1", "off", "false", "0", "disabled"}:
        raise ValueError("YUE2_MULTI_GPU debe ser auto, on u off")
    enabled = normalized not in {"off", "false", "0", "disabled"} and len(devices) > 1
    if enabled:
        # Un solo proceso coordina los dispositivos para no duplicar el modelo en VRAM.
        return [devices[0]], devices[1:], True
    return list(devices), [], False


def run() -> int:
    gradio_port = int(os.getenv("GRADIO_SERVER_PORT", "7875"))
    base_port = int(os.getenv("YUE2_BACKEND_PORT", "7876"))
    if not (1024 <= gradio_port <= 65535 and 1024 <= base_port <= 65535 and gradio_port != base_port):
        raise SystemExit("Puertos no válidos o duplicados")
    if not port_free(gradio_port):
        raise SystemExit(f"El puerto Gradio {gradio_port} está ocupado; no se interfiere.")

    binary = ROOT / "engine/prebuilt/v0.9.0/audiocpp_server"
    if not binary.is_file():
        raise SystemExit("Falta audio.cpp; ejecuta python scripts/install.py")

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = (
        "/usr/local/nvidia/lib64:/usr/local/cuda/lib64:" + env.get("LD_LIBRARY_PATH", "")
    ).rstrip(":")
    try:
        devices = available_cuda_devices(binary, env)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    requested = os.getenv("YUE2_GPU_DEVICES", "").strip()
    if requested:
        try:
            chosen = [int(part.strip()) for part in requested.split(",") if part.strip()]
        except ValueError as exc:
            raise SystemExit("YUE2_GPU_DEVICES debe ser una lista de índices, por ejemplo 0,1") from exc
        invalid = [device for device in chosen if device not in devices]
        if invalid:
            raise SystemExit(f"GPU no reconocida por audio.cpp: {invalid}; disponibles: {devices}")
        devices = list(dict.fromkeys(chosen))
    if not devices:
        raise SystemExit("No hay GPU CUDA seleccionadas.")

    try:
        worker_devices, secondary_devices, multi_gpu_enabled = gpu_plan(
            devices, os.getenv("YUE2_MULTI_GPU", "auto")
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    env["YUE2_MULTI_GPU"] = "auto" if multi_gpu_enabled else "off"
    env["YUE2_MULTI_GPU_DEVICES"] = ",".join(str(device) for device in secondary_devices)
    env["YUE2_MULTI_GPU_PRIMARY_DEVICE"] = str(worker_devices[0])

    children: list[tuple[int, int, subprocess.Popen, object]] = []
    urls: list[str] = []
    used_devices: list[int] = []
    try:
        print(f"GPU detectadas por audio.cpp: {devices}", flush=True)
        if multi_gpu_enabled:
            print(
                f"Modo Multi-GPU: GPU principal {worker_devices[0]}, "
                f"GPU secundarias {secondary_devices}; una canción puede repartir NAR/VAE.",
                flush=True,
            )
        else:
            print("Modo de workers independientes; Multi-GPU por canción desactivado.", flush=True)
        for slot, device in enumerate(worker_devices):
            # Separación de dos puertos para no chocar con servicios auxiliares habituales.
            port = base_port + 2 * slot
            if port > 65535 or port == gradio_port:
                print(f"GPU {device}: puerto {port} inválido; se omite.", flush=True)
                continue

            existing = model_entry(port)
            if existing is not None:
                existing_device = existing.get("device")
                if existing_device is not None and int(existing_device) != device:
                    print(f"GPU {device}: puerto {port} ya sirve la GPU {existing_device}; se omite.", flush=True)
                    continue
                if existing_device is None and slot > 0:
                    print(f"GPU {device}: el backend existente no informa su dispositivo; se omite por seguridad.", flush=True)
                    continue
                print(f"Reutilizando backend YuE2 en puerto {port} (GPU {device}).", flush=True)
                urls.append(f"http://127.0.0.1:{port}")
                used_devices.append(device)
                continue

            if not port_free(port):
                message = f"El puerto de backend {port} está ocupado por otro servicio."
                if not urls:
                    raise RuntimeError(message)
                print(f"AVISO: {message} GPU {device} omitida.", flush=True)
                continue

            config_path = ROOT / f"server-gpu{device}.json"
            config_path.write_text(json.dumps(backend_config(port, device), indent=2), encoding="utf-8")
            logs = ROOT / "logs"
            logs.mkdir(exist_ok=True)
            log_handle = (logs / f"backend-gpu{device}.log").open("a", encoding="utf-8")
            child = subprocess.Popen(
                [str(binary), "--config", str(config_path), "--no-ui", "--log"],
                cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT,
            )
            children.append((device, port, child, log_handle))
            if wait_for_backend(port, child):
                urls.append(f"http://127.0.0.1:{port}")
                used_devices.append(device)
                print(f"Backend YuE2 listo: GPU {device}, puerto {port}.", flush=True)
            else:
                stop_child(child)
                log_handle.close()
                children = [item for item in children if item[2] is not child]
                message = f"El backend de GPU {device} no inició; revisa logs/backend-gpu{device}.log"
                if not urls:
                    raise RuntimeError(message)
                print(f"AVISO: {message}. Se continúa con las GPU funcionales.", flush=True)

        if not urls:
            raise RuntimeError("No se pudo iniciar ningún backend YuE2.")
        env["YUE2_API_URLS"] = ",".join(urls)
        env["YUE2_API_URL"] = urls[0]
        env["YUE2_BACKEND_DEVICES"] = ",".join(str(device) for device in used_devices)
        env["YUE2_ACTIVE_GPU_COUNT"] = str(len(urls))
        print(f"Pool de inferencia activo: {len(urls)} worker(s), GPU {used_devices}.", flush=True)
        return subprocess.call([sys.executable, "-u", str(ROOT / "studio_fl.py")], cwd=ROOT, env=env)
    finally:
        for device, port, child, log_handle in reversed(children):
            stop_child(child)
            if not log_handle.closed:
                log_handle.close()


if __name__ == "__main__":
    raise SystemExit(run())
