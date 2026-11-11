"""Revisor independiente en CI con un modelo de Azure OpenAI (Responses API).

Usa el prompt del subagente local (.claude/agents/revisor.md), pero sin herramientas:
la spec, el diff y los archivos tocados van en el mensaje. Es otro proveedor de modelo
a propósito: no comparte los puntos ciegos de quien implementó.
El cambio se lee con git (REVISOR_HEAD), nunca del disco: en CI el disco es main y el PR
son solo datos. Sale con 0 solo si el veredicto es accept. Cualquier error falla cerrado.
"""

import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ROOT / ".claude" / "agents" / "revisor.md"
BASE = os.environ.get("REVISOR_BASE", "origin/main")
CAMBIO = os.environ.get("REVISOR_HEAD", "HEAD")
# shortcut: corta el contexto a 400k caracteres; si los PRs crecen, revisar archivo por archivo
LIMITE = 400_000

CONTEXTO_CI = """
## Esta ejecución (CI)
No tienes herramientas: no puedes ejecutar comandos ni leer archivos. Todo lo que puedes usar
viene en el mensaje: la spec (o la descripción del PR), el diff contra main y el contenido
completo de los archivos tocados. El gate es otro check obligatorio del PR: no lo evalúes.
Si te falta información para decidir, responde block.
"""

# La línea solo puede tener un veredicto: "accept | revise | block" (la plantilla) no cuenta
VEREDICTO = re.compile(r"\W*VEREDICTO:\W*(accept|revise|block)\W*", re.IGNORECASE)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout


def veredicto(texto: str) -> str | None:
    """Solo cuenta la última línea no vacía, como exige el prompt."""
    lineas = [linea for linea in texto.splitlines() if linea.strip()]
    encontrado = VEREDICTO.fullmatch(lineas[-1]) if lineas else None
    return encontrado.group(1).lower() if encontrado else None


def features(tocados: list[str]) -> list[str]:
    """Carpetas specs/features/NN-nombre que toca el cambio, sin la plantilla."""
    rutas = map(PurePosixPath, tocados)
    return sorted(
        {
            "/".join(p.parts[:3])
            for p in rutas
            if len(p.parts) > 3
            and p.parts[:2] == ("specs", "features")
            and p.parts[2] != "_plantilla"
        }
    )


def instrucciones() -> str:
    return PROMPT.read_text(encoding="utf-8").split("---", 2)[2] + CONTEXTO_CI  # sin frontmatter


def seccion(titulo: str, cuerpo: str) -> str:
    return f"\n\n===== {titulo} =====\n{cuerpo}"


def contexto() -> str:
    rango = f"{BASE}...{CAMBIO}"
    tocados = git("diff", "--name-only", "--diff-filter=d", rango).splitlines()  # sin borrados
    carpetas = features(tocados)
    partes = []
    for carpeta in carpetas:
        for spec in git("ls-tree", "--name-only", CAMBIO, f"{carpeta}/").splitlines():
            if spec.endswith(".md"):
                partes.append(seccion(f"SPEC {spec}", git("show", f"{CAMBIO}:{spec}")))
    if not carpetas:
        pedido = f"{os.environ.get('PR_TITLE', '')}\n\n{os.environ.get('PR_BODY', '')}".strip()
        partes.append(
            seccion("SIN FEATURE: LO PEDIDO EN EL PR", pedido or "(el PR no tiene descripción)")
        )
    partes.append(seccion(f"DIFF {rango}", git("diff", rango)))
    for f in tocados:
        partes.append(seccion(f"ARCHIVO {f}", git("show", f"{CAMBIO}:{f}")))
    texto = "".join(partes)
    return texto[:LIMITE] + ("\n\n[... contexto truncado]" if len(texto) > LIMITE else "")


def main() -> int:
    cliente = OpenAI(
        base_url=os.environ["AZURE_OPENAI_EVALUATOR_ENDPOINT"].rstrip("/") + "/",
        api_key=os.environ["AZURE_OPENAI_EVALUATOR_API_KEY"],
    )
    respuesta = cliente.responses.create(
        model=os.environ["AZURE_OPENAI_EVALUATOR_DEPLOYMENT"],
        instructions=instrucciones(),
        input=contexto(),
    )
    texto = respuesta.output_text
    print(texto)
    if resumen := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(resumen, "a", encoding="utf-8") as salida:
            salida.write(texto + "\n")
    decision = veredicto(texto)
    print(f"\n[REVISOR] Veredicto: {decision or 'ausente'}")
    return 0 if decision == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
