"""El harness también se prueba: los hooks deben bloquear lo que prometen."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"


def ejecutar(hook: str, payload: object) -> int:
    resultado = subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),  # como lo envía Claude Code
        capture_output=True,
        check=False,
    )
    return resultado.returncode


def bash(comando: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


@pytest.mark.parametrize(
    "comando",
    [
        "rm -rf /tmp/x",
        "git push origin main --force",
        "git reset --hard",
        "cat .env",
        "type the_agent_loop\\.env.local",
        "python -c \"print(open('.env').read())\"",
    ],
)
def test_validar_comando_bloquea(comando: str) -> None:
    assert ejecutar("validar_comando.py", bash(comando)) == 2


@pytest.mark.parametrize(
    "comando",
    ["ls -la", "cat the_agent_loop/.env.template", "python scripts/gate.py", "echo Ánimo"],
)
def test_validar_comando_permite(comando: str) -> None:
    assert ejecutar("validar_comando.py", bash(comando)) == 0


def test_validar_comando_falla_cerrado() -> None:
    assert ejecutar("validar_comando.py", ["no", "es", "un", "objeto"]) == 2


@pytest.mark.parametrize(
    ("comando", "esperado"),
    [
        ("git diff", 0),
        ("git diff --staged -- src/", 0),
        ("git status", 0),
        ("git log --oneline -5", 0),
        ("python scripts/gate.py", 0),
        ("git diff && rm -rf x", 2),
        ("git diff --output=x.txt", 2),
        ("git difftool", 2),
        ("git log; cat .env", 2),
        ("ruff format .", 2),
    ],
)
def test_solo_lectura(comando: str, esperado: int) -> None:
    assert ejecutar("solo_lectura.py", bash(comando)) == esperado
