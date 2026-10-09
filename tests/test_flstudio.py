"""Pruebas de flujos FL Studio, sin solicitar inferencia larga."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class FLStudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = load("flstudio_tools", ROOT / "flstudio_tools.py")
        cls.lab = load("studio_fl", ROOT / "studio_fl.py")

    def test_abc_pitch_and_meter(self):
        self.assertEqual(self.tools.abc_note(60), "C")
        self.assertEqual(self.tools.abc_note(72), "c")
        self.assertEqual(self.tools.abc_note(59), "B,")
        result = self.tools.make_abc([60, 62, 64, 65, 67, 69, 71, 72], bpm=128)
        self.assertIn("Q:1/4=128", result)
        self.assertIn("C D E F G A B c |", result)

    def test_cover_conditional_abc(self):
        abc = self.tools.make_abc([60, 62, 64, 65])
        payload = self.lab.yue_request("Piano pop", "[verse] Test", "melody", abc=abc)
        opts = payload["request"]["options"]
        self.assertEqual(opts["abc"], abc)
        self.assertEqual(opts["export_semantic"], "true")
        self.assertEqual(opts["guidance_scale"], "1.0")

    def test_semantic_prefix_and_bounds(self):
        request = self.lab.yue_request("Pop", "[verse] Test", "off",
                                       semantic=[0, 123, 32767], max_frames=250)
        options = request["request"]["options"]
        self.assertEqual(json.loads(options["semantic_prefix"]), [0, 123, 32767])
        self.assertEqual(options["semantic_max_tokens"], "250")
        with self.assertRaises(ValueError):
            self.lab.yue_request("Pop", "[verse] Test", "off", semantic=[32768], max_frames=250)
        with self.assertRaises(ValueError):
            self.lab.yue_request("Pop", "[verse] Test", "melody", semantic=[1], max_frames=250)

    def test_abc_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "song.wav"
            score = b"X:1\nK:C\nC D E F|\n"
            sem = b"[0,2,32767]"
            import base64
            fake = {"artifacts": [
                {"id": "semantic", "payload": base64.b64encode(sem).decode()},
                {"id": "score", "payload": base64.b64encode(score).decode()},
            ]}
            sem_out, score_out = self.lab.decode_artifacts(fake, base)
            self.assertEqual(json.loads(Path(sem_out).read_text()), [0, 2, 32767])
            self.assertEqual(Path(score_out).read_bytes(), score)

    def test_score_from_midi(self):
        from music21 import note, stream, tempo
        with tempfile.TemporaryDirectory() as td:
            midi = Path(td) / "idea.mid"
            part = stream.Stream()
            part.insert(0, tempo.MetronomeMark(number=120))
            for pitch in ("C4", "D4", "E4", "F4"):
                part.append(note.Note(pitch, quarterLength=1))
            part.write("midi", fp=str(midi))
            info = self.tools.score_from_midi(str(midi))
            self.assertIn("C C D D E E F F", info["abc"])
            self.assertEqual(info["bpm"], 120)

    def test_cover_from_wav_and_lyrics_without_abc(self):
        """El usuario debe poder crear un cover solo con audio + letra."""
        from unittest.mock import patch
        import soundfile as sf
        score = self.tools.make_abc([60, 62, 64, 65])
        with tempfile.TemporaryDirectory() as td:
            song = Path(td) / "idea_flstudio.wav"
            sf.write(song, np.zeros(22050, dtype=np.float32), 22050)
            result = str(Path(td) / "cover.wav")
            with patch.object(self.lab, "analyze_file", return_value={"abc": score, "source": "mezcla de audio"}) as analyze, \
                 patch.object(self.lab, "run_engine", return_value=(result, None, None, "prueba")) as engine:
                response = self.lab.cover_remix(
                    str(song), None, "", "pop rock", "[verse] Mi letra",
                    "Cover (mantener melodía aproximada)", 4, 1.0,
                    progress=lambda *a, **kw: None,
                )
            analyze.assert_called_once_with(str(song))
            submitted = engine.call_args.args[0]
            self.assertEqual(submitted["request"]["options"]["abc"], score)
            self.assertEqual(submitted["request"]["lyrics"], "[verse] Mi letra")
            self.assertEqual(response[0], result)
            self.assertTrue(response[3].endswith(".reference.abc"))
            self.assertTrue(Path(response[3]).exists())
            self.assertIn("automáticamente", response[4])

    def test_explicit_abc_skips_automatic_analysis(self):
        from unittest.mock import patch
        import soundfile as sf
        score = self.tools.make_abc([60, 62, 64, 65])
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "song.wav"
            sf.write(wav, np.zeros(22050, dtype=np.float32), 22050)
            with patch.object(self.lab, "analyze_file") as analyze, \
                 patch.object(self.lab, "run_engine",
                              return_value=(str(wav), None, str(wav.with_suffix(".abc")), "prueba")) as engine:
                self.lab.cover_remix(str(wav), None, score, "pop", "[verse] Test",
                    "Remix (nuevo arreglo sobre melodía)", 4, 1.,
                    progress=lambda *a, **kw: None)
            analyze.assert_not_called()
            self.assertEqual(engine.call_args.args[0]["request"]["options"]["abc"], score)

    def test_score_from_audio(self):
        import soundfile as sf
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "melodia.wav"
            sr = 11025
            seconds = 5
            t = np.arange(sr * seconds) / sr
            audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            sf.write(path, audio, sr)
            result = self.tools.score_from_audio(str(path))
            self.assertEqual(result["source"], "mezcla de audio")
            self.assertIn("K:C", result["abc"])


if __name__ == "__main__":
    unittest.main()
