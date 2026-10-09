"""Smoke de YuE2 con melodía ABC externa y exportación de tokens."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flstudio_tools import make_abc
from studio_fl import run_engine, yue_request

if __name__ == "__main__":
    score = make_abc([60, 62, 64, 65, 67, 69, 71, 72] * 2, 120, "Prueba funcional")
    req = yue_request("Acoustic pop, clean guitar, soft drums, warm vocals",
                      "[verse]\nHello morning light, now we begin.",
                      "melody", seed=1111, steps=4, cfg=1.0, abc=score, max_frames=220)
    wav, semantic, abc, info = run_engine(req)
    print("SMOKE_OK", wav, "codec", semantic, "score", abc, "info", info, flush=True)
    if not Path(wav).exists() or not semantic or not Path(semantic).exists():
        raise RuntimeError("La API no devolvió archivo WAV o tokens de continuación")
