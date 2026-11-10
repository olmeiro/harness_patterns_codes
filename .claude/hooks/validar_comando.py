import json
import re
import sys

# Ejemplo didáctico: no cubre todas las variantes
# posibles de ejecución de comandos.
PATRONES_PROHIBIDOS = [
    r"\brm\s+-rf(?:\s|$)",
    r"\bgit\s+reset\s+--hard(?:\s|$)",
    r"\bgit\s+push\b[^\n;]*--force\b",
    r"\bRemove-Item\b[^\n;]*-Recurse\b",
    # Secretos: en Windows nativo no hay sandbox, así que esta es la barrera real
    r"\.env\b(?!\.(?:template|example)\b)",
]


def main() -> None:
    try:
        # bytes + json.loads: decodifica UTF-8 aunque la consola de Windows sea cp1252
        data = json.loads(sys.stdin.buffer.read())
        comando = data.get("tool_input", {}).get("command", "")
        if not isinstance(comando, str):
            raise TypeError
    except Exception:  # payload inesperado: falla cerrado
        print("No se pudo validar la operación", file=sys.stderr)
        sys.exit(2)

    for patron in PATRONES_PROHIBIDOS:
        if re.search(patron, comando, re.IGNORECASE):
            print("Operación bloqueada por política.", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
