
import os
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI


# 1. CONFIGURACIÓN DE AZURE OPENAI

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=(
        os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        + "/openai/v1/"
    ),
)

DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# 2. ESTADO DEL AGENTE Y CONTEXTO DEL TURNO

@dataclass
class AgentState:
    history: list[Any] = field(default_factory=list)
    total_tokens: int = 0
    last_input_tokens: int = 0


@dataclass
class TurnContext:
    state: AgentState
    turn_number: int


# 3. SUBSISTEMA: MEDIDOR DE PRESUPUESTO

class BudgetMeter:
    def __init__(self, max_tokens: int = 50_000):
        self.max_tokens = max_tokens

    def on_turn(self, ctx: TurnContext):
        used = ctx.state.total_tokens

        print(f"[BudgetMeter] Tokens acumulados: {used}")

        if used >= self.max_tokens:
            raise RuntimeError("Presupuesto de tokens agotado")


# 4. SUBSISTEMA: COMPACTADOR

class Compactor:
    def __init__(
        self,
        client: OpenAI,
        deployment: str,
        context_window: int = 128_000,
        threshold: float = 0.8,
    ):
        self.client = client
        self.deployment = deployment
        self.context_window = context_window
        self.threshold = threshold

    def on_turn(self, ctx: TurnContext):
        state = ctx.state

        limit = self.context_window * self.threshold

        if state.last_input_tokens < limit:
            return

        if not state.history:
            return

        print("[Compactor] Compactando el contexto...")

        compacted = self.client.responses.compact(
            model=self.deployment,
            input=state.history,
        )

        # Reemplazar el historial por el contexto compactado
        state.history = list(compacted.output)

        # Reiniciar la referencia para la siguiente medición
        state.last_input_tokens = 0


# 5. REGISTRO DE SUBSISTEMAS

systems = [
    BudgetMeter(max_tokens=50_000),
    Compactor(
        client=client,
        deployment=DEPLOYMENT,
    ),
]


# 6. BUCLE PRINCIPAL DEL AGENTE

def agent_loop(prompts: list[str]):
    state = AgentState()

    for number, prompt in enumerate(prompts, start=1):

        print(f"\n========== TURNO {number} ==========")

        # Construir el contexto del turno
        ctx = TurnContext(
            state=state,
            turn_number=number,
        )

        # UPDATE METHOD:
        # Ejecutar cada subsistema en orden
        for system in systems:
            system.on_turn(ctx)

        # Agregar el mensaje del usuario
        state.history.append({
            "role": "user",
            "content": prompt,
        })

        # Llamar a Azure OpenAI Responses API
        response = client.responses.create(
            model=DEPLOYMENT,
            instructions="Responde en español con claridad.",
            input=state.history,
        )

        if response.status != "completed":
            raise RuntimeError(
                f"Respuesta no completada: {response.status}"
            )

        print(f"Agente: {response.output_text}")

        # Conservar los elementos devueltos por Responses
        state.history.extend(response.output)

        # Actualizar métricas para el siguiente turno
        if response.usage:
            state.total_tokens += response.usage.total_tokens
            state.last_input_tokens = (
                response.usage.input_tokens
            )


# 7. EJECUCIÓN

if __name__ == "__main__":
    agent_loop([
        "¿Qué es un agente de inteligencia artificial?",
        "Explícalo en términos más sencillos.",
        "¿Cómo se relaciona con LangGraph?",
    ])
