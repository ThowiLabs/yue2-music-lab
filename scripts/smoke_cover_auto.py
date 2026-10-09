"""Validación integrada: WAV de FL Studio -> melodía automática -> cover corto YuE2."""
from __future__ import annotations
import math
from pathlib import Path
import tempfile
import sys
import numpy as np
import soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flstudio_tools import analyze_file
from studio_fl import run_engine, yue_request

if __name__ == "__main__":
    sr = 11025
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "idea_flstudio.wav"
        signal = np.zeros(5 * sr, dtype=np.float32)
        for i, pitch in enumerate((261.63, 293.66, 329.63, 349.23, 392.00)):
            t = np.arange(sr, dtype=np.float32) / sr
            signal[i * sr:(i + 1) * sr] = 0.3 * np.sin(2 * math.pi * pitch * t)
        sf.write(file, signal, sr)
        reference = analyze_file(str(file))
        print("AUTO_ANALYZE_OK", reference["bpm"], reference["key"],
              len(reference["abc"]), flush=True)
        request = yue_request(
            "Acoustic pop with piano, gentle drums, melodic vocals",
            "[verse]\nSing my song in the morning light.",
            "melody", steps=4, cfg=1.,
            abc=reference["abc"], max_frames=220,
        )
        wav, tokens, abc, info = run_engine(request)
        assert Path(wav).exists() and tokens and Path(tokens).exists()
        print("AUTO_COVER_OK", wav, info, flush=True)
