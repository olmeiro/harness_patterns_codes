"""PostToolUse: tras cada Edit/Write formatea y revisa el archivo según su extensión.

También marca el gate como pendiente para que el hook Stop lo ejecute.
Agnóstico al proyecto: los umbrales viven en pyproject.toml, no aquí.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

PENDIENTE = Path(__file__).resolve().parents[1] / "gate_pendiente"

# Para soportar otro lenguaje basta añadir su extensión y sus comandos
# (la ruta del archivo se añade al final de cada uno).
COMPROBACIONES = {
    ".py": [
        ["ruff", "format"],
        ["ruff", "check", "--fix", "--output-format=concise"],
    ],
}
for ext in (".json", ".yaml", ".yml", ".js", ".ts", ".tsx", ".css"):
    COMPROBACIONES[ext] = [["prettier", "--write"]]


def main() -> None:
    PENDIENTE.touch()
    ruta = json.loads(sys.stdin.buffer.read()).get("tool_input", {}).get("file_path")
    errores = []
    for cmd in COMPROBACIONES.get(Path(ruta or "").suffix, []):
        exe = shutil.which(cmd[0])
        # shortcut: sin la herramienta instalada se omite en silencio; avisar si se quiere forzar su instalación
        if not exe:
            continue
        r = subprocess.run(
            [exe, *cmd[1:], ruta],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if r.returncode:
            errores.append((r.stdout + r.stderr).strip())

    if errores:
        print("\n".join(errores), file=sys.stderr)
        sys.exit(2)  # en PostToolUse no bloquea: Claude recibe el texto y corrige


if __name__ == "__main__":
    main()
