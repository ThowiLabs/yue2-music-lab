"""Instala únicamente el precompilado oficial CUDA 12.8 y los pesos GGUF necesarios."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v0.9.0"
ARCHIVE = f"audio-{RELEASE}-bin-ubuntu-x64-cuda12.8-colab.tar.gz"
SHA256 = "c9ed906f918246669c324f0d31f1b7dd80cbe003c35cf8a54932f333b57ca3f6"
URL = f"https://github.com/0xShug0/audio.cpp/releases/download/{RELEASE}/{ARCHIVE}"
MODEL_DIR = ROOT / "models" / "Yue2-3B-GGUF"
BINARY_DIR = ROOT / "engine" / "prebuilt" / RELEASE
REQUIRED = (
    "yue2-3b-q8_0.gguf",
    "yue2-vae-f16.gguf",
    "sidecars/yue2-model-config.json",
    "sidecars/yue2-generation-config.json",
    "sidecars/yue2-qwen.tiktoken",
    "sidecars/yue2-vae-config.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def install_binary() -> None:
    binary = BINARY_DIR / "audiocpp_server"
    spec = BINARY_DIR / "model_specs" / "yue2.json"
    if binary.is_file() and spec.is_file():
        print(f"Precompilado instalado: {binary}", flush=True)
        return
    BINARY_DIR.mkdir(parents=True, exist_ok=True)
    archive = BINARY_DIR.parent / ARCHIVE
    print(f"Descargando precompilado oficial {RELEASE} con reintentos...", flush=True)
    subprocess.run(
        ["curl", "--fail", "--location", "--retry", "4", "--retry-all-errors",
         "--retry-delay", "2", "--continue-at", "-", "--output", str(archive), URL],
        check=True,
    )
    actual = sha256(archive)
    if actual != SHA256:
        raise RuntimeError(f"SHA256 no coincide: {actual}")
    print("SHA256 del precompilado verificado", flush=True)
    with tarfile.open(archive, "r:gz") as tar:
        for name, destination in (
            ("./audiocpp_server", binary),
            ("./model_specs/yue2.json", spec),
        ):
            member = tar.getmember(name)
            if not member.isfile():
                raise RuntimeError("Paquete oficial sin archivo esperado: " + name)
            src = tar.extractfile(member)
            if src is None:
                raise RuntimeError("No se pudo extraer " + name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    binary.chmod(0o755)


def install_models() -> None:
    from huggingface_hub import snapshot_download

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("Descargando YuE2 Q8_0, VAE F16 y sidecars...", flush=True)
    snapshot_download(
        repo_id="audio-cpp/Yue2-3B-GGUF",
        allow_patterns=list(REQUIRED),
        local_dir=str(MODEL_DIR),
        max_workers=4,
    )
    missing = [str(MODEL_DIR / name) for name in REQUIRED
               if not (MODEL_DIR / name).is_file() or (MODEL_DIR / name).stat().st_size <= 0]
    if missing:
        raise RuntimeError("Faltan archivos: " + ", ".join(missing))
    for name in REQUIRED:
        file = MODEL_DIR / name
        print(f"{name}: {file.stat().st_size / (1024*1024):.1f} MiB", flush=True)


if __name__ == "__main__":
    install_binary()
    install_models()
    print("Instalación terminada. Ejecuta: python scripts/run.py", flush=True)
