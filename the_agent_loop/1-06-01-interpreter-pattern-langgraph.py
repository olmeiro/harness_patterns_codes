
import os
from typing import Any, Literal, TypedDict

from openai import OpenAI
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END


# ==========================================
# 1. Gramática del agente (DSL)
# ==========================================

class Paso(BaseModel):
    accion: Literal["agregar", "listar"]
    valor: str


class Programa(BaseModel):
    pasos: list[Paso]


# ==========================================
# 2. Clases del patrón Interpreter
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
# 3. Parser: Programa -> AST
# ==========================================

def parse(programa: Programa) -> Seq:
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
# 4. Estado compartido de LangGraph
# ==========================================

class Estado(TypedDict, total=False):
    solicitud: str
    programa: dict[str, Any]
    arbol: Expr
    tareas: list[str]
    resultados: list[Any]


# ==========================================
# 5. Cliente Azure OpenAI Responses API
# ==========================================

client = OpenAI(
    base_url=os.environ["AZURE_OPENAI_BASE_URL"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)


# ==========================================
# 6. Nodos de LangGraph
# ==========================================

def generar_programa(state: Estado):
    response = client.responses.parse(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        instructions=(
            "Convierte la solicitud en un programa "
            "de tareas. Solo puedes usar agregar y listar. "
            "Conserva el orden solicitado. "
            "Para listar, usa valor vacío."
        ),
        input=state["solicitud"],
        text_format=Programa,
    )

    if (
        response.status != "completed"
        or response.output_parsed is None
    ):
        raise ValueError("No se obtuvo un programa válido")

    return {
        "programa": response.output_parsed.model_dump()
    }


def construir_ast(state: Estado):
    programa = Programa.model_validate(state["programa"])

    return {
        "arbol": parse(programa)
    }


def ejecutar_ast(state: Estado):
    ctx = {
        "tareas": list(state.get("tareas", []))
    }

    resultados = state["arbol"].interpret(ctx)

    return {
        "tareas": ctx["tareas"],
        "resultados": resultados,
    }


# ==========================================
# 7. Construir el grafo
# ==========================================

builder = StateGraph(Estado)

builder.add_node("generar_programa", generar_programa)
builder.add_node("construir_ast", construir_ast)
builder.add_node("ejecutar_ast", ejecutar_ast)

builder.add_edge(START, "generar_programa")
builder.add_edge("generar_programa", "construir_ast")
builder.add_edge("construir_ast", "ejecutar_ast")
builder.add_edge("ejecutar_ast", END)

graph = builder.compile()


# ==========================================
# 8. Ejecutar el agente
# ==========================================

resultado = graph.invoke({
    "solicitud": (
        'Agrega la tarea "Revisar documentación de Azure" '
        "y después muéstrame todas mis tareas pendientes."
    ),
    "tareas": [],
})

print("Programa:", resultado["programa"])
print("Resultados:", resultado["resultados"])
print("Tareas:", resultado["tareas"])
