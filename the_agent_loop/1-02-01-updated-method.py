# Implementación en LangGraph del patrón Update Method para agentes conversacionales.
import os
from dataclasses import dataclass
from typing import Any, TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


# 1. CONFIGURACIÓN
load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=(
        os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        + "/"
    ),
)

DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# 2. ESTADO DE LANGGRAPH
class AgentState(TypedDict, total=False):
    user_input: str
    history: list[dict[str, Any]]
    answer: str
    total_tokens: int
    last_input_tokens: int
    turn_number: int


# 3. CONTEXTO DEL PATRÓN UPDATE METHOD
@dataclass
class TurnContext:
    history: list[dict[str, Any]]
    total_tokens: int
    last_input_tokens: int
    turn_number: int


# 4. SUBSISTEMA: BUDGET METER
class BudgetMeter:
    def __init__(self, max_tokens: int = 50_000):
        self.max_tokens = max_tokens

    def on_turn(self, ctx: TurnContext):
        print(
            f"[BudgetMeter] Tokens: "
            f"{ctx.total_tokens}/{self.max_tokens}"
        )

        if ctx.total_tokens >= self.max_tokens:
            raise RuntimeError("Presupuesto agotado")


# 5. SUBSISTEMA: COMPACTOR
class Compactor:
    def __init__(
        self,
        client: OpenAI,
        deployment: str,
        context_window: int,
        threshold: float = 0.8,
    ):
        self.client = client
        self.deployment = deployment
        self.context_window = context_window
        self.threshold = threshold

    def on_turn(self, ctx: TurnContext):
        limit = self.context_window * self.threshold

        if ctx.last_input_tokens < limit:
            return

        if not ctx.history:
            return

        print("[Compactor] Compactando contexto...")

        compacted = self.client.responses.compact(
            model=self.deployment,
            input=ctx.history,
        )

        ctx.history = [
            item.model_dump(mode="json", exclude_none=True)
            for item in compacted.output
        ]

        ctx.last_input_tokens = 0


# 6. REGISTRO DE SUBSISTEMAS
systems = [
    BudgetMeter(max_tokens=50_000),
    Compactor(
        client=client,
        deployment=DEPLOYMENT,
        context_window=int(
            os.getenv("AZURE_OPENAI_CONTEXT_WINDOW", "128000")
        ),
    ),
]


# 7. NODO: UPDATE HARNESS
def update_harness(state: AgentState) -> dict:
    ctx = TurnContext(
        history=list(state.get("history", [])),
        total_tokens=state.get("total_tokens", 0),
        last_input_tokens=state.get("last_input_tokens", 0),
        turn_number=state.get("turn_number", 0) + 1,
    )

    print(f"\n--- Turno {ctx.turn_number} ---")

    # PATRÓN UPDATE METHOD
    for system in systems:
        system.on_turn(ctx)

    return {
        "history": ctx.history,
        "turn_number": ctx.turn_number,
        "last_input_tokens": ctx.last_input_tokens,
    }


# 8. NODO: LLAMADA AL MODELO
def call_model(state: AgentState) -> dict:
    history = [
        *state.get("history", []),
        {
            "role": "user",
            "content": state["user_input"],
        },
    ]

    response = client.responses.create(
        model=DEPLOYMENT,
        instructions="Responde siempre en español.",
        input=history,
    )

    if response.status != "completed":
        raise RuntimeError(
            f"Respuesta no completada: {response.status}"
        )

    # Serializar los elementos para el checkpointer
    output_items = [
        item.model_dump(mode="json", exclude_none=True)
        for item in response.output
    ]

    usage = response.usage

    return {
        "history": history + output_items,
        "answer": response.output_text,
        "total_tokens": (
            state.get("total_tokens", 0)
            + (usage.total_tokens if usage else 0)
        ),
        "last_input_tokens": (
            usage.input_tokens if usage else 0
        ),
    }


# 9. CONSTRUCCIÓN DE LANGGRAPH
builder = StateGraph(AgentState)

builder.add_node("update_harness", update_harness)
builder.add_node("call_model", call_model)

builder.add_edge(START, "update_harness")
builder.add_edge("update_harness", "call_model")
builder.add_edge("call_model", END)

# Memoria entre turnos
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)


# 10. EJECUCIÓN
if __name__ == "__main__":
    config = {
        "configurable": {
            "thread_id": "conversacion-001"
        }
    }

    prompts = [
        "¿Qué es un agente de inteligencia artificial?",
        "Explícalo con palabras más sencillas.",
        "¿Cómo se relaciona con LangGraph?",
    ]

    for prompt in prompts:
        result = graph.invoke(
            {"user_input": prompt},
            config=config,
        )

        print(f"\nUsuario: {prompt}")
        print(f"Agente: {result['answer']}")


# Variales de entorno necesarias:
# AZURE_OPENAI_ENDPOINT=https://TU-RECURSO.openai.azure.com
# AZURE_OPENAI_API_KEY=TU-API-KEY
# AZURE_OPENAI_DEPLOYMENT=gpt-4o
# AZURE_OPENAI_CONTEXT_WINDOW=128000