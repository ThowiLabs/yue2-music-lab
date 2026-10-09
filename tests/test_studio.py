"""Pruebas de solicitud a YuE2, fin EOS y aislamiento."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = module("yue_studio", ROOT / "app.py")
        cls.runner = module("yue_run", ROOT / "scripts" / "run.py")

    def request(self, **changes):
        kw = dict(style="Orchestral salsa", lyrics="[Verse]\nCantemos.", cot="off",
                  seed=123, steps=8, guidance=1.01, sem_temperature=1,
                  sem_top_p=0.95, sem_top_k=100, sem_penalty=1.2,
                  sem_window=50, sem_min=200, abc_temperature=0.7,
                  abc_top_p=0.9, manual_limit=False, sem_max=9000)
        kw.update(changes)
        return self.app.payload(**kw)

    def test_auto_ends_by_eos_without_384_cap(self):
        req = self.request()
        self.assertEqual(req["model"], "yue2-q8")
        self.assertNotIn("semantic_max_tokens", req["request"]["options"])
        self.assertEqual(req["request"]["options"]["semantic_min_tokens"], "200")

    def test_explicit_limit_in_advanced_only(self):
        req = self.request(manual_limit=True, sem_max=2400)
        self.assertEqual(req["request"]["options"]["semantic_max_tokens"], "2400")

    def test_invalid_manual_limit_rejected(self):
        with self.assertRaises(ValueError):
            self.request(manual_limit=True, sem_max=100)

    def test_style_required(self):
        with self.assertRaises(ValueError):
            self.request(style=" ")

    def test_invalid_cot_rejected(self):
        with self.assertRaises(ValueError):
            self.request(cot="automatic")

    def test_valid_full_and_melody(self):
        for cot in ("full", "melody"):
            self.assertEqual(self.request(cot=cot)["request"]["options"]["cot"], cot)

    def test_sampling_limits(self):
        for changes in (
            {"seed": -1}, {"steps": 0}, {"sem_temperature": 6},
            {"sem_top_p": -0.1}, {"sem_penalty": 0}, {"sem_window": 0},
            {"sem_top_k": 0}, {"guidance": 21}, {"abc_top_p": 3},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.request(**changes)

    def test_backend_local_and_quantization(self):
        config = self.runner.backend_config(7876)
        self.assertEqual(config["host"], "127.0.0.1")
        self.assertEqual(config["backend"], "cuda")
        self.assertEqual(config["models"][0]["session_options"]["yue2.model_gguf"], "yue2-3b-q8_0.gguf")
        self.assertEqual(config["models"][0]["session_options"]["yue2.vae_gguf"], "yue2-vae-f16.gguf")


if __name__ == "__main__":
    unittest.main()
