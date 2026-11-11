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

# Crear o publicar commits no se bloquea: se pregunta a la persona.
# Cubre lo que no ven las reglas ask de settings.json: git -C <ruta>, git -c k=v, git.exe,
# rutas absolutas, sh -c "...", subprocess, líneas partidas y gh pr merge.
# No detecta alias de git (git ci). Puede preguntar de más, p. ej. git log --grep=revert.
CONFIRMAR = re.compile(
    r"\bgit(?:\.exe)?\b[^;&|\n]*?(?<![\w-])"
    r"(commit-tree|commit|push|merge|pull|cherry-pick|revert|rebase|am)(?![\w-])"
    r"|\bgh(?:\.exe)?\s+pr\s+merge\b",
    re.IGNORECASE,
)
CONTINUACION = re.compile(r"[\\`]\r?\n")  # \ en Bash y ` en PowerShell
PREGUNTAR = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "Crea o publica commits: solo si la persona lo pidió.",
    }
}


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

    if CONFIRMAR.search(CONTINUACION.sub(" ", comando)):
        print(json.dumps(PREGUNTAR))  # ASCII: la consola de Windows no escribe UTF-8
    sys.exit(0)


if __name__ == "__main__":
    main()
