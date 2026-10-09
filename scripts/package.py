"""Exporta el proyecto completo (incluyendo historia Git), sin datos ni pesos."""
from __future__ import annotations

from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "yue2-q8-gradio-v0.2.1.zip"


def paths() -> list[Path]:
    # Git conserva únicamente contenido intencional; excluye secretos/modelos.
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z"], cwd=ROOT, check=True,
        capture_output=True,
    )
    tracked = [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]
    git_files = [x for x in (ROOT / ".git").rglob("*") if x.is_file()
                 and x.name != "index.lock"]
    return sorted(set(tracked + git_files))


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    items = paths()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for item in items:
            archive.write(item, item.relative_to(ROOT))
    with zipfile.ZipFile(OUT) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP dañado: {bad}")
        names = set(archive.namelist())
        required = {"README.md", "app.py", ".git/HEAD",
                    "contexto/03-duracion-natural-y-interfaz.md"}
        if not required <= names:
            raise RuntimeError("Faltan archivos en el ZIP: " + str(required - names))
        print(f"ZIP_OK path={OUT} files={len(names)} size={OUT.stat().st_size}", flush=True)


if __name__ == "__main__":
    main()
