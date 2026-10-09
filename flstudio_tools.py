"""Herramientas locales para importar ideas musicales exportadas desde FL Studio.

La extracción de melodía desde una mezcla estéreo es heurística: para conservar
melodía exacta, usar exportación MIDI de FL Studio o una partitura ABC.
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import subprocess

import numpy as np

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aiff", ".aif"}
SCORE_EXTENSIONS = {".mid", ".midi", ".abc"}
MAX_BYTES = 150 * 1024 * 1024
MAX_DURATION = 20 * 60
PITCHES = ("C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B")
NOTES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def validate_file(value: str | None, extensions: set[str]) -> Path:
    if not value:
        raise ValueError("Sube un archivo de FL Studio primero.")
    path = Path(value).resolve()
    if not path.is_file() or path.suffix.lower() not in extensions:
        raise ValueError("Extensión no admitida: usa WAV/MP3/FLAC/M4A/OGG, MIDI o ABC.")
    if not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError("El archivo está vacío o supera 150 MiB.")
    return path


def audio_info(filename: str | Path) -> tuple[float, int]:
    path = validate_file(str(filename), AUDIO_EXTENSIONS)
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a:0",
           "-show_entries", "format=duration:stream=sample_rate", "-of", "json", str(path)]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if run.returncode or not run.stdout.strip():
        raise ValueError("FFprobe no pudo leer el audio.")
    try:
        info = json.loads(run.stdout)
        duration = float(info["format"]["duration"])
        sample_rate = int(info["streams"][0]["sample_rate"])
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError("No se encontró una pista de audio válida.") from exc
    if not 0 < duration <= MAX_DURATION or not 4000 <= sample_rate <= 384000:
        raise ValueError("Duración máxima: 20 min, con audio válido.")
    return duration, sample_rate


def snippet(path: Path, start: float, seconds: float = 24., sample_rate: int = 11025):
    duration, _ = audio_info(path)
    start = max(0.0, min(float(start), max(0.0, duration - 1.0)))
    seconds = min(float(seconds), duration - start, 60.0)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(start), "-i", str(path),
           "-t", str(seconds), "-vn", "-ac", "1", "-ar", str(sample_rate),
           "-f", "f32le", "pipe:1"]
    run = subprocess.run(cmd, capture_output=True, timeout=70, check=False)
    if run.returncode or len(run.stdout) < sample_rate * 2:
        raise ValueError("No se pudo decodificar el fragmento musical.")
    return np.frombuffer(run.stdout, dtype="<f4").copy(), sample_rate


def abc_note(midi: int) -> str:
    midi = int(midi)
    if midi < 36 or midi > 107:
        return "z"
    name = PITCHES[midi % 12]
    octave = midi // 12 - 1
    if octave < 4:
        return name + "," * (4 - octave)
    if octave == 4:
        return name
    return name.lower() + "'" * (octave - 5)


def make_abc(pitches: list[int | None], bpm: int = 120, title: str = "Idea FL Studio") -> str:
    if not 30 <= int(bpm) <= 300:
        bpm = 120
    lines = [f"X:1", f"T:{title[:70].replace(chr(10), ' ')}", "M:4/4", "L:1/8", f"Q:1/4={int(bpm)}", "K:C"]
    tokens = [abc_note(p) if p is not None else "z" for p in pitches[:320]]
    if not tokens or all(p == "z" for p in tokens):
        raise ValueError("No se identificaron notas; exporta MIDI desde FL Studio.")
    for i in range(0, len(tokens), 8):
        lines.append(" ".join(tokens[i:i + 8]) + " |")
    return "\n".join(lines) + "\n"


def score_from_midi(file: str) -> dict:
    from music21 import converter, chord, note, tempo
    path = validate_file(file, {".mid", ".midi"})
    midi = converter.parse(str(path))
    marks = list(midi.recurse().getElementsByClass(tempo.MetronomeMark))
    bpm = int(round(marks[0].getQuarterBPM())) if marks else 120
    bpm = max(30, min(300, bpm))
    grid: dict[int, int] = {}
    # Cada evento ocupa una o más corcheas. Priorizamos la nota superior.
    for obj in midi.flatten().notes:
        if isinstance(obj, note.Note):
            pitch = obj.pitch.midi
        elif isinstance(obj, chord.Chord):
            pitch = max(p.midi for p in obj.pitches)
        else:
            continue
        first = int(round(float(obj.offset) * 2))
        length = max(1, int(round(float(obj.duration.quarterLength) * 2)))
        if first < 0 or first >= 320:
            continue
        for pos in range(first, min(320, first + length)):
            grid[pos] = max(pitch, grid.get(pos, 0))
    if not grid:
        raise ValueError("El MIDI no contiene notas musicales.")
    pitches = [grid.get(i) for i in range(max(grid) + 1)]
    return {"abc": make_abc(pitches, bpm, title=path.stem),
            "bpm": bpm, "key": "partitura MIDI (tono original)", "confidence": "MIDI",
            "duration": 60.0 / bpm * len(pitches) / 2, "source": "MIDI exacto"}


def score_from_abc(file: str) -> dict:
    path = validate_file(file, {".abc"})
    if path.stat().st_size > 60000:
        raise ValueError("La partitura ABC excede el máximo de 60 KiB.")
    text = path.read_text(encoding="utf-8-sig")
    if not 10 < len(text) <= 50000 or not any(line.startswith("K:") for line in text.splitlines()):
        raise ValueError("La partitura ABC no contiene una tonalidad K: válida.")
    return {"abc": text, "bpm": None, "key": "en partitura ABC", "duration": None,
            "source": "ABC original", "confidence": "partitura original"}


def score_from_audio(file: str, *, ending: bool = False, position: float = 0.0) -> dict:
    import librosa

    path = validate_file(file, AUDIO_EXTENSIONS)
    duration, _ = audio_info(path)
    start = max(0., duration - 27.) if ending else min(max(0., float(position)), duration - 1.)
    y, sr = snippet(path, start, 24)
    hop = 512
    # Análisis ligero: extracción aproximada de BPM/tonalidad y melodía dominante.
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop)
    pitch_energy = chroma.mean(axis=1)
    major = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor = np.array([6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    choices = [(np.corrcoef(pitch_energy, np.roll(profile, key))[0, 1], key, mode)
               for key in range(12) for mode, profile in (("mayor", major), ("menor", minor))]
    _, key, mode = max(choices)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo = librosa.feature.tempo(onset_envelope=onset, sr=sr, hop_length=hop)
    bpm = int(round(float(tempo[0]))) if len(tempo) else 120
    bpm = max(50, min(220, bpm))
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=hop, fmin=170, fmax=1400)
    # Escoger pico fuerte por cada corchea evita una transcripción enorme.
    frames_per_eighth = max(1, round((60 / bpm / 2) * sr / hop))
    sequence = []
    for i in range(0, pitches.shape[1], frames_per_eighth):
        sl = slice(i, min(i + frames_per_eighth, pitches.shape[1]))
        scores = magnitudes[:, sl] * np.sqrt(np.maximum(pitches[:, sl], 1.))
        candidates = scores.max(axis=1)
        row = int(candidates.argmax())
        if candidates[row] < 0.003 or not np.isfinite(candidates[row]):
            sequence.append(None)
            continue
        local = pitches[row, sl]
        valid = local[local > 1]
        if valid.size == 0:
            sequence.append(None)
            continue
        midi_pitch = int(round(float(librosa.hz_to_midi(np.median(valid)))))
        sequence.append(midi_pitch if 45 <= midi_pitch <= 88 else None)
    if sum(p is not None for p in sequence) < 4:
        raise ValueError("No pude extraer una melodía fiable. Exporta MIDI desde FL Studio para un cover más exacto.")
    return {"abc": make_abc(sequence, bpm, title=path.stem), "bpm": bpm,
            "key": f"{NOTES[key]} {mode} (estimación)", "duration": duration,
            "source": "mezcla de audio", "confidence": "heurística; revisar melodía"}


def analyze_file(file: str, *, ending=False, position=0.) -> dict:
    suffix = Path(file).suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return score_from_audio(file, ending=ending, position=position)
    if suffix in (".mid", ".midi"):
        return score_from_midi(file)
    if suffix == ".abc":
        return score_from_abc(file)
    raise ValueError("Formato no compatible. Usa WAV, MP3, MIDI o ABC.")


def join_audio(original: str, generated: str, destination: str, *, fade: float = 1.5) -> str:
    length, _ = audio_info(original)
    other, _ = audio_info(generated)
    fade = min(max(0.1, float(fade)), length / 4, other / 4)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(original), "-i", str(generated),
           "-filter_complex",
           f"[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a];"
           f"[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[b];"
           f"[a][b]acrossfade=d={fade:.3f}:c1=tri:c2=tri[out]",
           "-map", "[out]", "-c:a", "pcm_s16le", str(destination)]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    if run.returncode:
        raise ValueError(f"No fue posible unir los WAV: {run.stderr[:400]}")
    return destination
