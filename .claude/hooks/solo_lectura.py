"""PreToolUse del subagente revisor: solo deja pasar lectura de git y el gate."""

import json
import re
import sys

# Sin encadenar, redirigir ni sustituir comandos, y sin --output (git lo usa para escribir archivos)
PERMITIDO = re.compile(
    r"git (?:diff|log|show|status)\b(?!.*--output)[^;&|<>`$\n]*|python scripts/gate\.py"
)


def main() -> None:
    try:
        comando = json.loads(sys.stdin.buffer.read())["tool_input"]["command"]
        permitido = PERMITIDO.fullmatch(comando.strip()) is not None
    except Exception:  # payload inesperado: falla cerrado
        permitido = False
    if not permitido:
        print(
            "El revisor solo puede ejecutar git diff/log/show/status y python scripts/gate.py",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
