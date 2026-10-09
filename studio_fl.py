"""YuE2 Studio para ideas de FL Studio: crear, covers, remix y extensiones."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import time
from uuid import uuid4
import urllib.error
import urllib.request
import wave

import gradio as gr

import app as legacy
from flstudio_tools import (
    AUDIO_EXTENSIONS, analyze_file, audio_info, join_audio, validate_file,
)

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
ALLOWED = str(OUTPUTS.resolve())
MAX_CODEC_FRAMES = 9000


def yue_request(style: str, lyrics: str, cot: str, seed: int = 20260920,
                steps: int = 4, cfg: float = 1.0, *,
                abc: str | None = None, semantic: list[int] | None = None,
                max_frames: int | None = None) -> dict:
    # Reutilizar la validación original de semilla, pasos y muestreo.
    request = legacy.payload(
        style=style, lyrics=lyrics, cot=cot, seed=seed, steps=steps, guidance=cfg,
        sem_temperature=1, sem_top_p=.95, sem_top_k=100,
        sem_penalty=1.2, sem_window=50, sem_min=200,
        abc_temperature=.7, abc_top_p=.9, manual_limit=False, sem_max=9000,
    )
    opts = request["request"]["options"]
    opts["export_semantic"] = "true"
    if abc:
        if cot == "off":
            raise ValueError("El condicionamiento ABC requiere CoT melody o full.")
        if not 10 < len(abc) < 50000 or "K:" not in abc:
            raise ValueError("La partitura ABC parece estar incompleta.")
        opts["abc"] = abc
    if semantic is not None:
        if cot != "off" and not abc:
            raise ValueError("La continuación semántica con CoT requiere también ABC.")
        if not 1 <= len(semantic) <= MAX_CODEC_FRAMES:
            raise ValueError("Los tokens de continuación exceden el límite.")
        if any(not isinstance(x, int) or isinstance(x, bool) or not 0 <= x < 32768 for x in semantic):
            raise ValueError("Token semántico inválido: deben ser enteros entre 0 y 32767.")
        opts["semantic_prefix"] = json.dumps(semantic, separators=(",", ":"))
    if max_frames is not None:
        minimum = max(200, len(semantic) if semantic else 0)
        if not minimum <= max_frames <= MAX_CODEC_FRAMES:
            raise ValueError("Límite de tokens incompatible con la duración o los tokens iniciales.")
        opts["semantic_max_tokens"] = str(int(max_frames))
    return request


def decode_artifacts(result: dict, base: Path) -> tuple[str | None, str | None]:
    score_file, codec_file = None, None
    for artifact in result.get("artifacts", []):
        kind = str(artifact.get("id") or artifact.get("kind") or "").lower()
        if not isinstance(artifact.get("payload"), str):
            continue
        data = base64.b64decode(artifact["payload"], validate=True)
        if len(data) > 1024 * 1024:
            continue
        if "semantic" in kind:
            try:
                values = json.loads(data.decode("utf-8"))
                if not isinstance(values, list) or not all(
                    isinstance(v, int) and not isinstance(v, bool) and 0 <= v < 32768 for v in values
                ):
                    continue
            except (UnicodeDecodeError, ValueError):
                continue
            codec_file = str(base.with_suffix(".semantic.json"))
            Path(codec_file).write_text(json.dumps(values), encoding="utf-8")
        elif "score" in kind or "abc" in kind:
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            score_file = str(base.with_suffix(".abc"))
            Path(score_file).write_text(content, encoding="utf-8")
    return codec_file, score_file


def run_engine(request: dict, progress=None) -> tuple[str, str | None, str | None, str]:
    if legacy.missing_components():
        raise ValueError("Faltan archivos de los modelos YuE2.")
    if not legacy.LOCK.acquire(blocking=False):
        raise ValueError("YuE2 está generando otra canción. Finaliza esa operación primero.")
    try:
        if progress:
            progress(0.01, desc="YuE2 componiendo y sintetizando en GPU 0")
        start = time.monotonic()
        payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
        if len(payload) > 700000:
            raise ValueError("La solicitud supera el tamaño seguro del motor.")
        req = urllib.request.Request(
            legacy.SERVER_URL + "/v1/tasks/run", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=7200) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read(1000).decode("utf-8", "replace")
            raise ValueError(f"El motor rechazó la solicitud ({exc.code}): {body}") from exc
        audio = result.get("audio")
        if not audio and result.get("named_audio_outputs"):
            audio = result["named_audio_outputs"][0]["audio"]
        if not audio:
            raise ValueError("La solicitud terminó sin devolver WAV.")
        wav = base64.b64decode(audio, validate=True)
        if not wav.startswith(b"RIFF") or wav[8:12] != b"WAVE":
            raise ValueError("YuE2 devolvió datos de audio inválidos.")
        OUTPUTS.mkdir(exist_ok=True)
        path = OUTPUTS / f"studio-{time.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}.wav"
        path.write_bytes(wav)
        codec, score = decode_artifacts(result, path)
        original_abc = request.get("request", {}).get("options", {}).get("abc")
        if original_abc and not score:
            abc_path = path.with_suffix(".abc")
            abc_path.write_text(original_abc, encoding="utf-8")
            score = str(abc_path)
        with wave.open(str(path), "rb") as file:
            seconds = file.getnframes() / file.getframerate()
        if progress:
            progress(1, desc="Audio completado")
        return str(path), codec, score, f"{seconds:.1f}s de audio · {time.monotonic()-start:.1f}s de cálculo"
    finally:
        legacy.LOCK.release()


def generate_original(style, lyrics, cot, seed, steps, cfg, manual, max_tokens,
                      progress=gr.Progress()):
    try:
        req = yue_request(style, lyrics, cot, int(seed), int(steps), float(cfg),
                          max_frames=int(max_tokens) if manual else None)
        path, semantic, score, info = run_engine(req, progress)
        return path, path, semantic, score, f"**Creación completa.** {info} · Tokens guardados para posteriores extensiones."
    except (ValueError, OSError) as exc:
        raise gr.Error(str(exc)) from exc


def prepare_reference(audio, midi, use_end: bool, offset: float):
    file = midi or audio
    try:
        info = analyze_file(file, ending=use_end, position=offset)
        description = f"**Origen:** {info['source']} · **BPM:** {info.get('bpm') or 'n/d'} · **Tonalidad:** {info.get('key')} · **Precisión:** {info.get('confidence')}."
        if info["source"] == "mezcla de audio":
            description += " La melodía automática puede equivocarse en mezclas polifónicas; proporciona MIDI desde FL Studio para mejores resultados."
        return info["abc"], description
    except (ValueError, OSError, TimeoutError) as exc:
        raise gr.Error(f"No se pudo analizar el archivo: {exc}") from exc


def cover_remix(audio, midi, score, style, lyrics, mode, steps, cfg,
                progress=gr.Progress()):
    if not audio and not midi:
        raise gr.Error("Sube la canción WAV/MP3 o una exportación MIDI de FL Studio.")
    try:
        if audio:
            validate_file(audio, AUDIO_EXTENSIONS)
        if midi:
            validate_file(midi, {".mid", ".midi", ".abc"})
        # Un WAV/MP3 más letra bastan: ABC y MIDI son mejoras opcionales.
        automatic = not score or not score.strip()
        reference = None
        if automatic:
            progress(0.02, desc="Analizando automáticamente la referencia musical")
            reference = analyze_file(midi or audio)
            score = reference["abc"]
        if mode == "Nueva idea inspirada en la referencia":
            # Inspiración libre: conservar tempo/tono estimados en la descripción.
            bpm = reference.get("bpm") if reference else None
            key = reference.get("key") if reference else None
            if not bpm:
                bpm_line = next((line for line in score.splitlines() if line.startswith("Q:")), "")
                bpm = bpm_line.split("=")[-1] if "=" in bpm_line else None
            hints = f", approximately {bpm} BPM" if bpm else ""
            if key:
                hints += f", key {key}"
            req = yue_request(style + hints, lyrics, "off", steps=int(steps), cfg=float(cfg))
        else:
            req = yue_request(style, lyrics, "melody", steps=int(steps), cfg=float(cfg), abc=score)
        path, codec, produced_score, info = run_engine(req, progress)
        if not produced_score:
            OUTPUTS.mkdir(exist_ok=True)
            partitura = Path(path).with_suffix(".reference.abc")
            partitura.write_text(score, encoding="utf-8")
            produced_score = str(partitura)
        note = "Nueva interpretación, no modificación de la grabación original."
        if automatic and not midi:
            note += " Melodía inferida automáticamente del audio: puede diferir de la original."
        return path, path, codec, produced_score, f"**{mode} completado.** {info}. {note}"
    except (ValueError, OSError) as exc:
        raise gr.Error(str(exc)) from exc


def extend_fl(audio, midi, score, style, lyrics, length_sec, crossfade_sec,
              steps, cfg, progress=gr.Progress()):
    try:
        if not audio:
            raise ValueError("Para extender tu audio, sube un WAV/MP3/FLAC. Se conservará íntegro salvo el solapamiento del fundido.")
        validate_file(audio, AUDIO_EXTENSIONS)
        duration, _ = audio_info(audio)
        if duration < 3:
            raise ValueError("El fragmento debe tener al menos 3 segundos.")
        if midi:
            validate_file(midi, {".mid", ".midi", ".abc"})
        if not score or not score.strip():
            progress(0.02, desc="Extrayendo automáticamente la melodía de los últimos compases")
            score = analyze_file(midi or audio, ending=True)["abc"]
        max_frames = int(float(length_sec) * 25)
        request = yue_request(style, lyrics, "melody", steps=int(steps),
                              cfg=float(cfg), abc=score, max_frames=max_frames)
        generated, codec, generated_score, info = run_engine(request, progress)
        OUTPUTS.mkdir(exist_ok=True)
        destination = OUTPUTS / f"flstudio-extend-{uuid4().hex[:8]}.wav"
        joined = join_audio(audio, generated, str(destination), fade=float(crossfade_sec))
        combined_length, _ = audio_info(joined)
        return joined, joined, generated, codec, generated_score, (
            f"**Extensión creada:** {combined_length:.1f}s finales. {info}. "
            "Se conservó la grabación original y se anexó una nueva interpretación "
            "de YuE2 con crossfade. No es continuación exacta del audio ni garantiza idéntico timbre."
        )
    except (ValueError, OSError, TimeoutError) as exc:
        raise gr.Error(str(exc)) from exc


def load_semantics(file: str) -> list[int]:
    path = validate_file(file, {".json"})
    if path.stat().st_size > 75000:
        raise ValueError("El JSON de tokens excede el máximo.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not 1 <= len(data) <= 9000 or any(
        type(x) is not int or not 0 <= x < 32768 for x in data
    ):
        raise ValueError("Sube un JSON de tokens semánticos YuE2 (0–32767).")
    return data


def continue_yue(semantics, style, lyrics, append_seconds, steps, cfg,
                 progress=gr.Progress()):
    try:
        tokens = load_semantics(semantics)
        if len(tokens) + int(append_seconds * 25) > MAX_CODEC_FRAMES:
            raise ValueError("Historia + extensión supera 9000 tokens. Utiliza menos segundos o un prefijo más corto.")
        req = yue_request(style, lyrics, "off", steps=int(steps), cfg=float(cfg),
                          semantic=tokens, max_frames=len(tokens) + int(append_seconds * 25))
        path, new_tokens, score, info = run_engine(req, progress)
        return path, path, new_tokens, (
            f"**Continuación desde {len(tokens)} tokens:** {info}. "
            "YuE2 vuelve a sintetizar los tokens anteriores; el audio puede variar ligeramente."
        )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise gr.Error(str(exc)) from exc


with gr.Blocks(title="YuE2 · FL Studio Music Lab") as demo:
    gr.Markdown("# YuE2 · Music Lab\nGeneración de canciones, covers y extensiones experimentales de proyectos FL Studio.")
    state = gr.Markdown(legacy.status())
    with gr.Tabs():
        with gr.Tab("Crear canción"):
            with gr.Row():
                with gr.Column():
                    style = gr.Textbox(label="Estilo musical", lines=3,
                        value="Latin pop, crisp drums, expressive vocals, warm keys, polished studio production")
                    lyrics = gr.Textbox(label="Letra", lines=9,
                        value="[verse]\nThe night is turning into day.\n[chorus]\nWe're making music all the way.")
                    submit = gr.Button("Generar canción", variant="primary")
                with gr.Column():
                    music = gr.Audio(label="Resultado YuE2", type="filepath")
                    download = gr.File(label="Descargar WAV")
                    semfile = gr.File(label="Tokens para extender después (JSON)")
                    abcfile = gr.File(label="Partitura generada (ABC)")
                    message = gr.Markdown("El audio acaba naturalmente por EOS.")
            with gr.Accordion("Calidad y duración · avanzado", open=False):
                with gr.Row():
                    cot = gr.Dropdown(["off", "melody", "full"], value="off", label="Planificación (CoT)")
                    seed = gr.Number(label="Semilla", value=20260920, precision=0)
                    steps = gr.Slider(4, 48, value=4, step=1, label="Pasos NAR")
                    cfg = gr.Slider(0, 5, value=1.0, step=.01, label="CFG")
                cap = gr.Checkbox(value=False, label="Limitar duración manualmente (por defecto final natural)")
                cap_tokens = gr.Number(label="Máximo de tokens semánticos", value=9000, minimum=200, maximum=9000, precision=0)
            submit.click(generate_original,
                inputs=[style, lyrics, cot, seed, steps, cfg, cap, cap_tokens],
                outputs=[music, download, semfile, abcfile, message], concurrency_limit=1)
        with gr.Tab("Cover / Remix"):
            gr.Markdown("**Cover en 3 pasos:** sube tu WAV/MP3, escribe la letra y pulsa **Crear cover**. YuE2 extrae una referencia melódica automáticamente. No tienes que subir MIDI ni escribir ABC.")
            with gr.Row():
                with gr.Column():
                    cover_audio = gr.File(label="1. Tu canción de FL Studio · WAV / MP3", type="filepath",
                                          file_types=[".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aiff"])
                    cover_lyrics = gr.Textbox(label="2. Letra de tu cover", lines=8,
                        placeholder="[verse]\nTu primera estrofa...\n[chorus]\nTu coro...", value="")
                    cover_style = gr.Textbox(value="Smooth pop-rock cover, lead singer, acoustic guitar, drums, warm bass",
                                             label="Estilo de la nueva versión (opcional cambiarlo)", lines=2)
                    cover_mode = gr.Dropdown(
                        ["Cover (mantener melodía aproximada)", "Remix (nuevo arreglo sobre melodía)", "Nueva idea inspirada en la referencia"],
                        value="Cover (mantener melodía aproximada)", label="Tipo de generación")
                    cover_run = gr.Button("3. Crear cover / remix automáticamente", variant="primary")
                    with gr.Accordion("Opcional · MIDI, partitura ABC y ajustes avanzados", open=False):
                        gr.Markdown("Una exportación MIDI de FL Studio mejora la precisión. También puedes inspeccionar y modificar la partitura, pero **no es obligatorio** pulsar Analizar.")
                        cover_midi = gr.File(label="MIDI o ABC (opcional)", type="filepath", file_types=[".mid", ".midi", ".abc"])
                        cover_offset = gr.Number(value=0, minimum=0, label="Analizar desde el segundo")
                        cover_analyze = gr.Button("Analizar previamente (opcional)")
                        cover_analysis = gr.Markdown()
                        cover_abc = gr.Textbox(label="Partitura ABC opcional", lines=8, placeholder="Vacío = análisis automático al crear el cover")
                        with gr.Row():
                            cover_steps = gr.Slider(4, 24, value=4, step=1, label="NAR")
                            cover_cfg = gr.Slider(0, 5, value=1., step=.01, label="CFG")
                with gr.Column():
                    cover_result = gr.Audio(label="Nueva interpretación", type="filepath")
                    cover_download = gr.File(label="Descargar WAV")
                    cover_sem = gr.File(label="Tokens para continuar")
                    cover_score = gr.File(label="ABC generado")
                    cover_message = gr.Markdown()
            # Si cambia la referencia, nunca reutilizar accidentalmente el ABC anterior.
            cover_audio.change(lambda: ("", ""), outputs=[cover_abc, cover_analysis])
            cover_midi.change(lambda: ("", ""), outputs=[cover_abc, cover_analysis])
            cover_analyze.click(lambda a, m, p: prepare_reference(a, m, False, p),
                inputs=[cover_audio, cover_midi, cover_offset], outputs=[cover_abc, cover_analysis])
            cover_run.click(cover_remix,
                inputs=[cover_audio, cover_midi, cover_abc, cover_style, cover_lyrics, cover_mode, cover_steps, cover_cfg],
                outputs=[cover_result, cover_download, cover_sem, cover_score, cover_message], concurrency_limit=1)
        with gr.Tab("Extender FL Studio"):
            gr.Markdown("**Conserva tu demo y añade música nueva.** Se analiza la parte final de tu canción, YuE2 genera una sección nueva y se une mediante crossfade. No es una continuación exacta del timbre como Suno.")
            with gr.Row():
                with gr.Column():
                    extend_audio = gr.File(label="Tu demo FL Studio incompleta · WAV/MP3", type="filepath",
                                           file_types=[".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff"])
                    extend_midi = gr.File(label="Opcional: MIDI/ABC de la melodía final", type="filepath",
                                          file_types=[".mid", ".midi", ".abc"])
                    analyze_end = gr.Button("1. Analizar los últimos compases")
                    analysis_end = gr.Markdown()
                    extend_abc = gr.Textbox(label="Motivo final (ABC editable)", lines=7)
                    extend_style = gr.Textbox(label="Cómo debe continuar", lines=3,
                        value="Continue the established Latin pop groove, same approximate tempo and key, natural instrumental transition, new verse and chorus.")
                    extend_lyrics = gr.Textbox(label="Letra de continuación", lines=6,
                        value="[verse]\nHere's where the story carries on.\n[chorus]\nWe'll keep the rhythm going strong.")
                    length = gr.Slider(15, 120, value=45, step=5, label="Máximo de segundos nuevos (aproximado)")
                    fade = gr.Slider(0.2, 5.0, value=1.5, step=.1, label="Transición (crossfade) en segundos")
                    with gr.Row():
                        ext_steps = gr.Slider(4, 24, value=4, step=1, label="NAR")
                        ext_cfg = gr.Slider(0, 5, value=1.0, step=.01, label="CFG")
                    ext_submit = gr.Button("2. Extender y unir audio", variant="primary")
                with gr.Column():
                    extended = gr.Audio(label="Canción con continuación", type="filepath")
                    ext_download = gr.File(label="Descargar canción completa")
                    ext_new = gr.Audio(label="Sección nueva sin unir", type="filepath")
                    ext_sem = gr.File(label="Tokens de la generación")
                    ext_score = gr.File(label="ABC generado")
                    ext_message = gr.Markdown()
            analyze_end.click(lambda a, m: prepare_reference(a, m, True, 0),
                inputs=[extend_audio, extend_midi], outputs=[extend_abc, analysis_end])
            ext_submit.click(extend_fl,
                inputs=[extend_audio, extend_midi, extend_abc, extend_style, extend_lyrics,
                        length, fade, ext_steps, ext_cfg],
                outputs=[extended, ext_download, ext_new, ext_sem, ext_score, ext_message], concurrency_limit=1)
        with gr.Tab("Continuar una canción YuE2"):
            gr.Markdown("**Continuación real desde tokens YuE2.** Usa el archivo JSON que se descarga al generar una canción en la primera pestaña. Este método no acepta directamente MP3 externos.")
            with gr.Row():
                with gr.Column():
                    sem_source = gr.File(label="Tokens semánticos (.json) de una canción anterior",
                                         type="filepath", file_types=[".json"])
                    sem_style = gr.Textbox(label="Estilo para continuar", lines=3,
                        value="Latin pop, expressive vocals, continue the original harmony and instruments")
                    sem_lyrics = gr.Textbox(label="Letra de continuación", lines=6,
                        value="[verse]\nThe next part of this song begins.\n[chorus]\nThe melody goes on again.")
                    sem_seconds = gr.Slider(10, 90, value=30, step=5, label="Máximo segundos a añadir")
                    with gr.Row():
                        sem_steps = gr.Slider(4, 24, value=4, step=1, label="NAR")
                        sem_cfg = gr.Slider(0, 5, value=1, step=.01, label="CFG")
                    sem_submit = gr.Button("Continuar desde tokens", variant="primary")
                with gr.Column():
                    sem_player = gr.Audio(label="Canción regenerada + continuación", type="filepath")
                    sem_download = gr.File(label="Descargar resultado WAV")
                    next_sem = gr.File(label="Nuevos tokens para otra extensión")
                    sem_info = gr.Markdown()
            sem_submit.click(continue_yue, inputs=[sem_source, sem_style, sem_lyrics, sem_seconds, sem_steps, sem_cfg],
                outputs=[sem_player, sem_download, next_sem, sem_info], concurrency_limit=1)
    gr.Button("Actualizar estado del motor", size="sm").click(legacy.status, outputs=state)


def gradio_auth():
    """Sin login exclusivamente si se solicita GRADIO_DISABLE_AUTH=1."""
    if os.getenv("GRADIO_DISABLE_AUTH", "0") == "1":
        return None
    return legacy.credentials()


if __name__ == "__main__":
    OUTPUTS.mkdir(exist_ok=True)
    login = gradio_auth()
    if login is None:
        print("AVISO: Gradio sin login; cualquier persona con el enlace puede acceder.", flush=True)
    demo.queue(max_size=3).launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "7875")),
        auth=login,
        share=os.getenv("GRADIO_SHARE", "1") == "1",
        allowed_paths=[ALLOWED], show_error=False,
        max_file_size="150mb",
    )
