"""Prueba acotada de la continuación de tokens generados por YuE2."""
from __future__ import annotations
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio_fl import run_engine, yue_request

if __name__ == "__main__":
    files = sorted((Path(__file__).resolve().parents[1] / "outputs").glob("studio-*.semantic.json"))
    if not files:
        raise RuntimeError("Falta una generación previa con exportación de tokens")
    prefix = json.loads(files[-1].read_text())
    target = len(prefix) + 220
    if target > 9000:
        raise RuntimeError("El prefijo es demasiado largo para esta prueba")
    req = yue_request("Acoustic pop, clean guitar, soft drums, warm vocals",
                      "[verse]\nHello morning light, now we begin.\n[chorus]\nAnd now the melody grows.",
                      "off", steps=4, cfg=1., seed=1111, semantic=prefix, max_frames=target)
    wav, new_sem, score, info = run_engine(req)
    if not wav or not new_sem:
        raise RuntimeError("Continuación no produjo tokens")
    result = json.loads(Path(new_sem).read_text())
    if len(result) < len(prefix):
        raise RuntimeError("La continuación perdió la historia original")
    print("CONTINUACION_OK",len(prefix),"->",len(result),info,wav,flush=True)
