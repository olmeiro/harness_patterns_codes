
import json
import os
from collections import deque
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=(
        os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        + "/"
    ),
)

MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]

# Base de datos simulada
ORDERS = {
    "1001": "pendiente",
    "1002": "en_preparacion",
    "1003": "entregado",
}

# Herramienta disponible para el modelo
TOOLS = [
    {
        "type": "function",
        "name": "update_order_status",
        "description": "Actualiza el estado de un pedido.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": [
                        "pendiente",
                        "en_preparacion",
                        "entregado",
                        "cancelado",
                    ],
                },
            },
            "required": ["order_id", "status"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def update_order_status(order_id: str, status: str) -> dict:
    """Herramienta que modifica un pedido simulado."""
    if order_id not in ORDERS:
        return {"error": f"Pedido {order_id} no encontrado"}

    ORDERS[order_id] = status
    return {"order_id": order_id, "status": status}


# =====================================================
# 1. CLASE BASE DEL PATRÓN STATE
# =====================================================

class State:
    def on_message(self, session, message):
        raise RuntimeError("Este estado no admite mensajes")

    def on_approve(self, session):
        raise RuntimeError("Este estado no admite aprobación")

    def on_deny(self, session):
        raise RuntimeError("Este estado no admite denegación")

    def step(self, session):
        return self


# =====================================================
# 2. ESTADOS CONCRETOS
# =====================================================

class Idle(State):
    def on_message(self, session, message):
        session.pending_input = [
            {"role": "user", "content": message}
        ]
        return CallingModel()


class CallingModel(State):
    def on_message(self, session, message):
        session.queue.append(message)
        return self

    def step(self, session):
        request = {
            "model": MODEL,
            "instructions": (
                "Eres un asistente de gestión de pedidos. "
                "Usa las herramientas cuando necesites cambiar "
                "el estado de un pedido. Responde en español."
            ),
            "input": session.pending_input,
            "tools": TOOLS,
            "parallel_tool_calls": False,
            "store": True,
        }

        if session.response_id:
            request["previous_response_id"] = session.response_id

        response = client.responses.create(**request)

        session.response_id = response.id
        session.pending_input = []

        calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if calls:
            return AwaitingApproval(calls[0])

        session.final_answer = response.output_text
        return Done()


class AwaitingApproval(State):
    def __init__(self, call):
        self.call = call

    def on_message(self, session, message):
        session.queue.append(message)
        return self

    def on_approve(self, session):
        return RunningTool(self.call)

    def on_deny(self, session):
        session.add_tool_result(
            self.call,
            {
                "status": "denied",
                "message": "El usuario rechazó la ejecución.",
            },
        )
        return CallingModel()


class RunningTool(State):
    def __init__(self, call):
        self.call = call

    def on_message(self, session, message):
        session.queue.append(message)
        return self

    def step(self, session):
        try:
            if self.call.name != "update_order_status":
                raise ValueError("Herramienta no permitida")

            args = json.loads(self.call.arguments)

            result = update_order_status(
                order_id=args["order_id"],
                status=args["status"],
            )
        except (ValueError, KeyError, TypeError) as exc:
            result = {"error": str(exc)}

        session.add_tool_result(self.call, result)
        return CallingModel()


class Done(State):
    def step(self, session):
        print(f"\nAgente: {session.final_answer}")
        return Idle()


# =====================================================
# 3. SESIÓN DEL AGENTE
# =====================================================

@dataclass
class AgentSession:
    state: State = field(default_factory=Idle)
    queue: deque = field(default_factory=deque)
    response_id: str | None = None
    pending_input: list = field(default_factory=list)
    final_answer: str = ""

    def transition(self, new_state):
        print(
            f"[STATE] {type(self.state).__name__} "
            f"-> {type(new_state).__name__}"
        )
        self.state = new_state

    def add_tool_result(self, call, result):
        self.pending_input = [
            {
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result),
            }
        ]

    def on_message(self, message):
        next_state = self.state.on_message(self, message)
        self.transition(next_state)
        self.advance()

    def on_approve(self):
        next_state = self.state.on_approve(self)
        self.transition(next_state)
        self.advance()

    def on_deny(self):
        next_state = self.state.on_deny(self)
        self.transition(next_state)
        self.advance()

    def advance(self):
        """Avanza hasta Idle o hasta requerir aprobación."""
        while not isinstance(
            self.state, (Idle, AwaitingApproval)
        ):
            next_state = self.state.step(self)
            self.transition(next_state)

        # Procesar mensajes acumulados cuando ya esté libre.
        while isinstance(self.state, Idle) and self.queue:
            message = self.queue.popleft()
            next_state = self.state.on_message(self, message)
            self.transition(next_state)

            while not isinstance(
                self.state, (Idle, AwaitingApproval)
            ):
                next_state = self.state.step(self)
                self.transition(next_state)


# =====================================================
# 4. INTERFAZ DE CONSOLA
# =====================================================

def main():
    session = AgentSession()

    print("Agente de pedidos iniciado.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        if isinstance(session.state, AwaitingApproval):
            call = session.state.call
            print("\n[APROBACIÓN REQUERIDA]")
            print(f"Herramienta: {call.name}")
            print(f"Argumentos: {call.arguments}")

            answer = input(
                "¿Aprobar? (si/no): "
            ).strip().lower()

            if answer == "si":
                session.on_approve()
            elif answer == "no":
                session.on_deny()
            else:
                print("Responde si o no.")
            continue

        message = input("\nUsuario: ").strip()

        if message.lower() == "salir":
            break

        if message:
            session.on_message(message)


if __name__ == "__main__":
    main()
