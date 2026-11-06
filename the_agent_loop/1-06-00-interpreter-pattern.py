
import os
from typing import Literal
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 1. Definir la gramática del agente (DSL)
# ==========================================

class Paso(BaseModel):
    accion: Literal["agregar", "listar"]
    valor: str

class Programa(BaseModel):
    pasos: list[Paso]


# ==========================================
# 2. Definir los nodos del Interpreter
# ==========================================

class Expr:
    def interpret(self, ctx):
        raise NotImplementedError


class Agregar(Expr):
    def __init__(self, valor):
        self.valor = valor

    def interpret(self, ctx):
        ctx["tareas"].append(self.valor)
        return f"Tarea agregada: {self.valor}"


class Listar(Expr):
    def interpret(self, ctx):
        return list(ctx["tareas"])


class Seq(Expr):
    def __init__(self, pasos):
        self.pasos = pasos

    def interpret(self, ctx):
        return [
            paso.interpret(ctx)
            for paso in self.pasos
        ]


# ==========================================
# 3. Parser: Programa -> Árbol de objetos
# ==========================================

def parse(programa):
    if not 1 <= len(programa.pasos) <= 10:
        raise ValueError("Cantidad de pasos no permitida")

    nodos = []

    for paso in programa.pasos:
        if paso.accion == "agregar":
            if not paso.valor.strip():
                raise ValueError("La tarea no puede estar vacía")
            nodos.append(Agregar(paso.valor))

        elif paso.accion == "listar":
            nodos.append(Listar())

    return Seq(nodos)


# ==========================================
# 4. Azure OpenAI - Responses API
# ==========================================

client = OpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

response = client.responses.parse(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    instructions=(
        "Convierte la solicitud del usuario en un programa "
        "de acciones. Solo puedes agregar o listar tareas. "
        "Conserva el orden solicitado. Para listar, "
        "utiliza una cadena vacía en valor."
    ),
    input=(
        'Agrega la tarea "Revisar documentación de Azure" '
        "y después muéstrame todas mis tareas pendientes."
    ),
    text_format=Programa,
)

if response.status != "completed":
    raise RuntimeError("Respuesta incompleta")

programa = response.output_parsed

if programa is None:
    raise ValueError("No se obtuvo un programa válido")


# ==========================================
# 5. Interpretar y ejecutar el programa
# ==========================================

ctx = {"tareas": []}  # Workspace de ejemplo

tree = parse(programa)

resultados = tree.interpret(ctx)

print("Programa:", programa.model_dump())
print("Resultados:", resultados)
print("Workspace:", ctx)
