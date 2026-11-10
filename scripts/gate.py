"""Gate determinista: lint, formato, tipos y tests.

Igual en todos los proyectos: qué revisar (rutas, reglas, umbrales) se configura
en pyproject.toml. Ejecuta todo y resume, para ver todos los fallos en una vuelta.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    ("Lint", ["ruff", "check", "."]),
    ("Formato", ["ruff", "format", "--check", "."]),
    ("Tipos", ["mypy"]),  # rutas en [tool.mypy] files
    ("Tests", ["pytest", "-q"]),  # rutas en [tool.pytest.ini_options] testpaths
]


def main() -> int:
    fallos = []
    for nombre, argumentos in CHECKS:
        print(f"\n[GATE] Ejecutando: {nombre}", flush=True)
        resultado = subprocess.run([sys.executable, "-m", *argumentos], cwd=ROOT, check=False)
        estado = "PASS" if resultado.returncode == 0 else "FAIL"
        print(f"[GATE] {estado}: {nombre}", flush=True)
        if resultado.returncode != 0:
            fallos.append(nombre)

    if fallos:
        print(f"\n[GATE] FAIL: {', '.join(fallos)}")
        return 1
    print("\n[GATE] Todas las comprobaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
