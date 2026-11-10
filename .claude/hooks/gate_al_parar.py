"""Stop: si Claude editó archivos desde el último gate verde, ejecuta el gate.

Si falla, sale con 2: Claude recibe el resumen como motivo para seguir corrigiendo.
Claude Code corta el bucle solo tras 8 continuaciones seguidas.
"""

import subprocess
import sys
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parents[1]
PENDIENTE = CLAUDE_DIR / "gate_pendiente"  # lo crea post_edit.py
GATE = CLAUDE_DIR.parent / "scripts" / "gate.py"


def main() -> int:
    if not PENDIENTE.exists():
        return 0
    r = subprocess.run(
        [sys.executable, str(GATE)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if r.returncode == 0:
        PENDIENTE.unlink(missing_ok=True)
        return 0
    # Solo el final: ahí está el resumen y no satura el contexto
    print(f"El gate falló. Corrígelo antes de terminar:\n{r.stdout[-4000:]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
