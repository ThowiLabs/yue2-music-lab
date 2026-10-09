"""Interfaz Gradio mínima para YuE2 Q8 mediante el servidor oficial de audio.cpp."""
from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
import secrets
import threading
import time
import urllib.error
import urllib.request
import wave
from uuid import uuid4

import gradio as gr

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models" / "Yue2-3B-GGUF"
OUTPUTS = ROOT / "outputs"
SERVER_URL = os.getenv("YUE2_API_URL", "http://127.0.0.1:7876").rstrip("/")
LOCK = threading.Lock()
REQUIRED = (
    "yue2-3b-q8_0.gguf",
    "yue2-vae-f16.gguf",
    "sidecars/yue2-model-config.json",
    "sidecars/yue2-generation-config.json",
    "sidecars/yue2-qwen.tiktoken",
    "sidecars/yue2-vae-config.json",
)


def get_json(path: str, timeout: float = 4) -> dict:
    with urllib.request.urlopen(f"{SERVER_URL}{path}", timeout=timeout) as response:
        return json.load(response)


def missing_components() -> list[str]:
    return [name for name in REQUIRED if not (MODEL_DIR / name).is_file() or (MODEL_DIR / name).stat().st_size == 0]


def status() -> str:
    missing = missing_components()
    try:
        ctypes.CDLL("libcuda.so.1")
        cuda = "disponible"
    except OSError:
        cuda = "no disponible"
    try:
        health = get_json("/health")
        models = get_json("/v1/models").get("data", [])
        entry = next((m for m in models if m.get("id") == "yue2-q8"), None)
        server = f"activo ({health.get('backend', '?')}); modelo {'cargado' if entry and entry.get('loaded') else 'disponible'}"
    except (OSError, ValueError, KeyError):
        server = "sin conexión (ejecuta scripts/run.py)"
    return f"**Motor:** {server} · **CUDA:** {cuda} · **Pesos:** {'completos' if not missing else 'faltan: ' + ', '.join(missing)}"


def payload(
    style: str, lyrics: str, cot: str, seed: int, steps: int,
    guidance: float, sem_temperature: float, sem_top_p: float, sem_top_k: int,
    sem_penalty: float, sem_window: int, sem_min: int,
    abc_temperature: float, abc_top_p: float,
    manual_limit: bool, sem_max: int,
) -> dict:
    """Permitir al modelo acabar por EOS; nunca fijar un límite corto por defecto."""
    if not style.strip() or not lyrics.strip():
        raise ValueError("Escribe estilo musical y letra.")
    if len(style) > 2000 or len(lyrics) > 12000:
        raise ValueError("El estilo o la letra son demasiado largos.")
    if cot not in ("off", "melody", "full"):
        raise ValueError("Planificación no admitida.")
    if not 4 <= int(steps) <= 48 or not 0 <= int(seed) <= 2147483647:
        raise ValueError("Pasos o semilla fuera de rango.")
    if not 0.0 <= float(guidance) <= 20.0:
        raise ValueError("Escala de guía fuera de rango.")
    if not (0.0 <= float(sem_temperature) <= 5.0 and 0.0 <= float(sem_top_p) <= 1.0):
        raise ValueError("Parámetros de muestreo inválidos.")
    if not 1 <= int(sem_top_k) <= 1000 or not 0.01 <= float(sem_penalty) <= 10:
        raise ValueError("Parámetros de muestreo inválidos.")
    if not 1 <= int(sem_window) <= 10000 or not 0 <= int(sem_min) <= 9000:
        raise ValueError("Límites semánticos inválidos.")
    if not (0 <= float(abc_temperature) <= 5 and 0 <= float(abc_top_p) <= 1):
        raise ValueError("Parámetros de planificación inválidos.")
    options = {
        "style": style.strip(),
        "cot": cot,
        "guidance_scale": str(float(guidance)),
        "semantic_temperature": str(float(sem_temperature)),
        "semantic_top_p": str(float(sem_top_p)),
        "semantic_top_k": str(int(sem_top_k)),
        "semantic_repetition_penalty": str(float(sem_penalty)),
        "semantic_penalty_window": str(int(sem_window)),
        "semantic_min_tokens": str(int(sem_min)),
        "abc_temperature": str(float(abc_temperature)),
        "abc_top_p": str(float(abc_top_p)),
    }
    # El valor predeterminado del motor es 9000 tokens (~6 min a 25 fps);
    # antes de ese techo, la generación finaliza naturalmente con EOS.
    if manual_limit:
        if not int(sem_min) <= int(sem_max) <= 30000:
            raise ValueError("El límite manual debe ser >= mínimo y <= 30000.")
        options["semantic_max_tokens"] = str(int(sem_max))
    return {
        "model": "yue2-q8",
        "request": {
            "lyrics": lyrics.strip(),
            "seed": int(seed),
            "num_inference_steps": int(steps),
            "options": options,
        },
    }


def generate(
    style: str, lyrics: str, cot: str, seed: float, steps: float,
    guidance: float, sem_temperature: float, sem_top_p: float, sem_top_k: float,
    sem_penalty: float, sem_window: float, sem_min: float,
    abc_temperature: float, abc_top_p: float, manual_limit: bool, sem_max: float,
    progress=gr.Progress(),
):
    if missing_components():
        raise gr.Error("Los pesos no están completos. Revisa la instalación.")
    try:
        request_body = payload(
            style, lyrics, cot, int(seed), int(steps), float(guidance),
            float(sem_temperature), float(sem_top_p), int(sem_top_k),
            float(sem_penalty), int(sem_window), int(sem_min),
            float(abc_temperature), float(abc_top_p), manual_limit, int(sem_max),
        )
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    if not LOCK.acquire(blocking=False):
        raise gr.Error("Ya hay una generación activa desde esta interfaz.")
    try:
        progress(0.01, desc="Generando canción hasta que el modelo indique su final")
        request = urllib.request.Request(
            SERVER_URL + "/v1/tasks/run",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=7200) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            details = exc.read(1500).decode("utf-8", errors="replace")
            raise gr.Error(f"Error del motor (HTTP {exc.code}): {details}") from exc
        except (OSError, ValueError) as exc:
            raise gr.Error(f"No se completó la generación: {str(exc)[:500]}") from exc

        audio = result.get("audio")
        if not audio and result.get("named_audio_outputs"):
            audio = result["named_audio_outputs"][0]["audio"]
        if not audio:
            raise gr.Error("El modelo terminó sin devolver audio.")
        try:
            wav = base64.b64decode(audio, validate=True)
        except ValueError as exc:
            raise gr.Error("Respuesta de audio corrupta.") from exc
        if not wav.startswith(b"RIFF") or b"WAVE" not in wav[:16]:
            raise gr.Error("Respuesta no válida: esperaba WAV.")
        OUTPUTS.mkdir(exist_ok=True)
        output = OUTPUTS / f"yue2-{time.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}.wav"
        output.write_bytes(wav)
        with wave.open(str(output), "rb") as stream:
            seconds = stream.getnframes() / stream.getframerate()
        progress(1.0, desc="Canción completada")
        return str(output), str(output), (
            f"**Canción generada:** {seconds:.1f} segundos · "
            f"{len(wav) / 1048576:.1f} MiB · WAV sin pérdida"
        )
    finally:
        LOCK.release()


def credentials() -> tuple[str, str]:
    password = os.getenv("GRADIO_PASSWORD")
    if not password:
        keyfile = ROOT / ".gradio-auth"
        if keyfile.exists():
            password = keyfile.read_text(encoding="utf-8").strip()
        else:
            password = secrets.token_urlsafe(18)
            fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(password + "\n")
    return os.getenv("GRADIO_USER", "admin"), password


with gr.Blocks(title="YuE2 Q8 Studio") as demo:
    gr.Markdown("# YuE2 Studio\nCrea canciones con YuE2-3B Q8 · CUDA · WAV.")
    current = gr.Markdown(status())
    with gr.Row():
        with gr.Column(scale=3):
            style = gr.Textbox(
                label="Estilo", lines=3,
                value="Orchestral salsa, expressive brass, piano montuno, bass tumbao, congas, warm lead vocal, studio recording",
                placeholder="Género, instrumentos, voz, ambiente y producción",
            )
            lyrics = gr.Textbox(
                label="Letra", lines=10,
                value="[Verse]\nThe lights of the city are shining tonight.\nMy heart is dancing in the warm moonlight.\n[Chorus]\nStay with me, let the music play.\nWe'll keep on dancing until the day.",
                placeholder="[Verse]\n...\n[Chorus]\n...",
            )
            submit = gr.Button("Generar canción completa", variant="primary")
            gr.Markdown(
                "La canción termina cuando YuE2 predice su token de finalización. "
                "El motor mantiene su techo interno de seguridad de 9000 tokens "
                "(aprox. 6 minutos), sin el anterior corte de 15 segundos."
            )
        with gr.Column(scale=2):
            player = gr.Audio(label="Resultado", type="filepath")
            download = gr.File(label="Descargar WAV")
            feedback = gr.Markdown("Listo para generar.")
    with gr.Accordion("Avanzado · ajustes del modelo", open=False):
        gr.Markdown("Deja los valores predeterminados para una primera prueba; los cambios pueden afectar calidad, duración y VRAM.")
        with gr.Row():
            cot = gr.Dropdown(["off", "melody", "full"], value="off", label="Planificación (CoT)")
            seed = gr.Number(label="Semilla", value=20260920, precision=0, minimum=0, maximum=2147483647)
            steps = gr.Slider(label="Pasos acústicos NAR", minimum=4, maximum=48, step=1, value=8)
        with gr.Row():
            guidance = gr.Slider(label="Escala de guía CFG", minimum=0, maximum=5, step=0.01, value=1.01)
            sem_temperature = gr.Slider(label="Creatividad semántica (temperatura)", minimum=0, maximum=3, step=0.05, value=1)
            sem_top_p = gr.Slider(label="Semantic top-p", minimum=0, maximum=1, step=0.01, value=0.95)
            sem_top_k = gr.Slider(label="Semantic top-k", minimum=1, maximum=300, step=1, value=100)
        with gr.Row():
            sem_penalty = gr.Slider(label="Penalización de repetición", minimum=0.5, maximum=3, step=0.05, value=1.2)
            sem_window = gr.Slider(label="Ventana antirrepeticiones", minimum=1, maximum=500, step=1, value=50)
            sem_min = gr.Number(label="Mínimo tokens antes de permitir final", value=200, precision=0, minimum=0, maximum=9000)
        with gr.Row():
            abc_temperature = gr.Slider(label="Temperatura de planificación ABC", minimum=0, maximum=3, step=0.05, value=0.7)
            abc_top_p = gr.Slider(label="Top-p de planificación ABC", minimum=0, maximum=1, step=0.01, value=0.9)
        manual_limit = gr.Checkbox(
            label="Aplicar límite manual de tokens (desactivado = final natural/EOS)",
            value=False,
        )
        with gr.Group(visible=False) as manual_group:
            sem_max = gr.Number(
                label="Máximo tokens semánticos",
                value=9000, precision=0, minimum=0, maximum=30000,
                info="Aproximadamente 25 tokens por segundo. Reducir este valor puede cortar la canción.",
            )
        manual_limit.change(
            fn=lambda active: gr.update(visible=active),
            inputs=manual_limit, outputs=manual_group,
        )
    submit.click(
        fn=generate,
        inputs=[
            style, lyrics, cot, seed, steps, guidance,
            sem_temperature, sem_top_p, sem_top_k, sem_penalty, sem_window, sem_min,
            abc_temperature, abc_top_p, manual_limit, sem_max,
        ],
        outputs=[player, download, feedback],
        concurrency_limit=1,
    )
    gr.Button("Actualizar estado del motor", size="sm").click(fn=status, outputs=current)

if __name__ == "__main__":
    OUTPUTS.mkdir(exist_ok=True)
    port = int(os.getenv("GRADIO_SERVER_PORT", "7875"))
    user, password = credentials()
    print(f"YuE2 Gradio puerto {port}; usuario={user}; contraseña fuera del repositorio.", flush=True)
    demo.queue(max_size=2).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=port,
        share=os.getenv("GRADIO_SHARE", "1") == "1",
        auth=(user, password),
        allowed_paths=[str(OUTPUTS.resolve())],
        show_error=False,
        prevent_thread_lock=False,
    )
