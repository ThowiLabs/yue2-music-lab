"""Prueba manual optativa: genera un fragmento breve con la API local."""
import base64
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
data = {
    "model": "yue2-q8",
    "request": {
        "lyrics": "[Verse]\nMorning light is shining over me.\nCan you hear this little melody?\n[Chorus]\nSing along and let the rhythm go.",
        "seed": 20260920,
        "num_inference_steps": 4,
        "options": {
            "style": "English, simple acoustic pop, steady drums, melodic warm vocal",
            "cot": "off",
            "semantic_max_tokens": "160",
            "semantic_min_tokens": "48",
        },
    },
}
url = "http://127.0.0.1:7876/v1/tasks/run"
request = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=1200) as response:
    answer = json.load(response)
audio = answer.get("audio")
if not audio:
    raise RuntimeError("Respuesta sin audio: " + repr(answer)[:500])
wav = base64.b64decode(audio)
if not wav.startswith(b"RIFF"):
    raise RuntimeError("Respuesta no WAV")
out = ROOT / "outputs" / "prueba-yue2-q8.wav"
out.write_bytes(wav)
print("SMOKE_OK", out, "size=", len(wav), "timing=", answer.get("timing"), flush=True)
