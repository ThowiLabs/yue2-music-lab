"""Comprobaciones del cuaderno Kaggle incluido en el repositorio."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

NOTEBOOK = Path(__file__).resolve().parents[1] / "kaggle" / "YuE2_Music_Lab_ThowiLabs.ipynb"


class KaggleNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

    def test_all_code_cells_parse(self):
        for cell in self.notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))

    def test_no_separate_status_or_shutdown_cells(self):
        ids = [c.get("id") for c in self.notebook["cells"]]
        self.assertEqual(ids[-1], "start")
        self.assertFalse({"step-seven", "status", "shutdown-title", "shutdown"} & set(ids))

    def test_gradio_is_foreground_and_interruptible(self):
        cell = next(c for c in self.notebook["cells"] if c.get("id") == "start")
        script = "".join(cell["source"])
        self.assertIn("for line in music_lab_process.stdout:", script)
        self.assertIn("exit_code = music_lab_process.wait()", script)
        self.assertIn("except KeyboardInterrupt:", script)
        self.assertIn("os.killpg(music_lab_process.pid, signal.SIGTERM)", script)
        self.assertIn("start_new_session=True", script)
        self.assertNotIn("LOG_FILE", script)

    def test_repo_is_cloned(self):
        cell = next(c for c in self.notebook["cells"] if c.get("id") == "clone")
        self.assertIn("https://github.com/thowilabs/yue2-music-lab.git", "".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
