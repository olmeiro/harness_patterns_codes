import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

# ========================================
# 1. AZURE OPENAI
# ========================================

load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # el .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
)


# ========================================
# 2. PATRÓN COMPOSITE
# ========================================


# Interfaz común (Component)
class Block(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def redact(self) -> "Block":
        pass

    @abstractmethod
    def count(self) -> int:
        pass


# Elemento individual (Leaf)
@dataclass
class TextBlock(Block):
    text: str

    def render(self) -> str:
        return self.text

    def redact(self) -> Block:
        clean = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w+\b", "[EMAIL_OCULTO]", self.text)

        clean = re.sub(r"(?i)\b(token|password|api_key)\s*[:=]\s*\S+", r"\1=[OCULTO]", clean)

        return TextBlock(clean)

    def count(self) -> int:
        return 1


# Contenedor (Composite)
@dataclass
class CompositeBlock(Block):
    name: str
    children: list[Block]

    def render(self) -> str:
        lines = [f"[{self.name}]"]

        for child in self.children:
            for line in child.render().splitlines():
                lines.append("  " + line)

        return "\n".join(lines)

    def redact(self) -> Block:
        return CompositeBlock(self.name, [child.redact() for child in self.children])

    def count(self) -> int:
        return sum(child.count() for child in self.children)


# ========================================
# 3. ESTADO DE LANGGRAPH
# ========================================


class TicketState(TypedDict):
    ticket: Block
    ticket_limpio: NotRequired[Block]
    contexto: NotRequired[str]
    cantidad_bloques: NotRequired[int]
    analisis: NotRequired[str]


# ========================================
# 4. NODOS DEL GRAFO
# ========================================


# Nodo 1: Depurar contenido
def depurar_ticket(state: TicketState):
    ticket = state["ticket"]

    return {"ticket_limpio": ticket.redact()}


# Nodo 2: Preparar contexto
def preparar_contexto(state: TicketState):
    ticket = state["ticket_limpio"]

    return {"contexto": ticket.render(), "cantidad_bloques": ticket.count()}


# Nodo 3: Análisis con LLM
def analizar_ticket(state: TicketState):

    response = client.responses.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        instructions=(
            "Eres un analista de soporte técnico. "
            "Analiza el ticket y responde en español con: "
            "1. Resumen del problema. "
            "2. Prioridad: alta, media o baja. "
            "3. Posible causa. "
            "4. Acción recomendada. "
            "No inventes información."
        ),
        input=state["contexto"],
        store=False,
    )

    return {"analisis": response.output_text}


# ========================================
# 5. CONSTRUIR LANGGRAPH
# ========================================

builder = StateGraph(TicketState)

builder.add_node("depurar", depurar_ticket)
builder.add_node("preparar", preparar_contexto)
builder.add_node("analizar", analizar_ticket)

builder.add_edge(START, "depurar")
builder.add_edge("depurar", "preparar")
builder.add_edge("preparar", "analizar")
builder.add_edge("analizar", END)

graph = builder.compile()


# ========================================
# 6. TICKET DE EJEMPLO
# ========================================

ticket = CompositeBlock(
    name="Ticket #1042",
    children=[
        CompositeBlock(
            name="Descripción",
            children=[
                TextBlock("La plataforma de pagos devuelve error 504. Contacto: ana@empresa.com")
            ],
        ),
        CompositeBlock(
            name="Comentarios",
            children=[
                TextBlock("Cliente: falla en 8 de 10 intentos."),
                TextBlock("Soporte: error reproducido."),
            ],
        ),
        CompositeBlock(
            name="Resultado de herramienta",
            children=[
                TextBlock("API /checkout: HTTP 504 Gateway Timeout."),
                CompositeBlock(
                    name="Logs",
                    children=[
                        TextBlock("Timeout en payments-api después de 30s."),
                        TextBlock("token=abc123456"),
                    ],
                ),
            ],
        ),
    ],
)


# ========================================
# 7. EJECUTAR EL AGENTE
# ========================================

result = graph.invoke({"ticket": ticket})

print("=== CONTEXTO DEPURADO ===")
print(result["contexto"])

print("\n=== CANTIDAD DE BLOQUES ===")
print(result["cantidad_bloques"])

print("\n=== ANÁLISIS DEL AGENTE ===")
print(result["analisis"])
