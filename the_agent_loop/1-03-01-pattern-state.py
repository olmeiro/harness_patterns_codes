"""Ejemplo del patrón State con LangGraph y Azure OpenAI Responses API.

Ejecución:
    uv add langgraph openai python-dotenv
    uv run state_langgraph.py
"""

import json
import os
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
)
MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]

# Simulación de una base de datos. NO es persistente.
ORDERS = {
    "1001": "pendiente",
    "1002": "en_preparacion",
    "1003": "entregado",
}
ALLOWED_STATUSES = {"pendiente", "en_preparacion", "entregado", "cancelado"}

TOOLS = [
    {
        "type": "function",
        "name": "update_order_status",
        "description": "Actualiza el estado de un pedido por su identificador.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": sorted(ALLOWED_STATUSES),
                },
            },
            "required": ["order_id", "status"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


class AgentState(TypedDict, total=False):
    # Datos compartidos entre los nodos.
    pending_input: list[dict[str, Any]]
    response_id: str | None
    tool_call: dict[str, Any] | None
    approved: bool | None
    final_answer: str


def idle(state: AgentState) -> dict:
    # Entrada del turno; la consulta llegará por pending_input.
    return {"tool_call": None, "approved": None, "final_answer": ""}


def calling_model(state: AgentState) -> dict:
    request: dict[str, Any] = {
        "model": MODEL,
        "instructions": (
            "Eres un asistente de pedidos. Responde en español. "
            "Cuando el usuario pida cambiar el estado de un pedido, "
            "solicita la herramienta update_order_status. "
            "La aplicación requiere aprobación humana antes de ejecutarla. "
            "Si el resultado indica 'denied', informa del rechazo "
            "sin volver a solicitar la misma operación."
        ),
        "input": state["pending_input"],
        "tools": TOOLS,
        "parallel_tool_calls": False,
        "store": True,
    }
    if state.get("response_id"):
        request["previous_response_id"] = state["response_id"]

    response = client.responses.create(**request)
    calls = [item for item in response.output if item.type == "function_call"]

    if len(calls) > 1:
        raise RuntimeError("Este ejemplo solo admite una herramienta por paso")

    if calls:
        call = calls[0]
        return {
            "response_id": response.id,
            "pending_input": [],
            "tool_call": {
                "call_id": call.call_id,
                "name": call.name,
                "arguments": call.arguments,
            },
            "final_answer": "",
        }

    return {
        "response_id": response.id,
        "pending_input": [],
        "tool_call": None,
        "final_answer": response.output_text,
    }


def route_after_model(state: AgentState) -> Literal["awaiting_approval", "done"]:
    return "awaiting_approval" if state.get("tool_call") else "done"


def awaiting_approval(state: AgentState) -> dict:
    call = state["tool_call"]
    # No ejecutar acciones con efectos secundarios antes de interrupt().
    decision = interrupt(
        {
            "question": "¿Apruebas la ejecución de esta herramienta?",
            "name": call["name"],
            "arguments": call["arguments"],
        }
    )
    return {"approved": decision is True}


def route_after_approval(state: AgentState) -> Literal["running_tool", "deny_tool"]:
    return "running_tool" if state.get("approved") is True else "deny_tool"


def tool_output(call: dict, result: dict) -> dict:
    return {
        "pending_input": [
            {
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": json.dumps(result, ensure_ascii=False),
            }
        ],
        "tool_call": None,
    }


def running_tool(state: AgentState) -> dict:
    call = state["tool_call"]
    try:
        if call["name"] != "update_order_status":
            raise ValueError("Herramienta no permitida")
        args = json.loads(call["arguments"])
        order_id, status = args["order_id"], args["status"]
        if status not in ALLOWED_STATUSES:
            raise ValueError("Estado de pedido no permitido")
        if order_id not in ORDERS:
            raise ValueError("Pedido no encontrado")
        ORDERS[order_id] = status
        result = {"ok": True, "order_id": order_id, "status": status}
    except (ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "error": str(exc)}
    return tool_output(call, result)


def deny_tool(state: AgentState) -> dict:
    return tool_output(
        state["tool_call"],
        {"status": "denied", "message": "Acción rechazada por el usuario."},
    )


def done(state: AgentState) -> dict:
    return {}


builder = StateGraph(AgentState)
builder.add_node("idle", idle)
builder.add_node("calling_model", calling_model)
builder.add_node("awaiting_approval", awaiting_approval)
builder.add_node("running_tool", running_tool)
builder.add_node("deny_tool", deny_tool)
builder.add_node("done", done)

builder.add_edge(START, "idle")
builder.add_edge("idle", "calling_model")
builder.add_conditional_edges("calling_model", route_after_model)
builder.add_conditional_edges("awaiting_approval", route_after_approval)
builder.add_edge("running_tool", "calling_model")
builder.add_edge("deny_tool", "calling_model")
builder.add_edge("done", END)

# Checkpoint local; para producción usar persistencia duradera.
graph = builder.compile(checkpointer=InMemorySaver())


def main() -> None:
    config = {"configurable": {"thread_id": "pedidos-demo-1"}}
    print("Agente con LangGraph y Responses API")
    print("Escribe 'salir' para terminar.")
    print("Pedidos simulados:", ORDERS)

    while True:
        message = input("\nUsuario: ").strip()
        if message.lower() == "salir":
            break
        if not message:
            continue

        result = graph.invoke(
            {"pending_input": [{"role": "user", "content": message}]},
            config=config,
        )

        # LangGraph puede pausar el flujo tantas veces como sea necesario.
        while "__interrupt__" in result:
            request = result["__interrupt__"][0].value
            print("\n[Aprobación requerida]")
            print("Herramienta:", request["name"])
            print("Argumentos:", request["arguments"])

            decision = ""
            while decision not in ("si", "no"):
                decision = input("¿Aprobar? (si/no): ").strip().lower()

            result = graph.invoke(
                Command(resume=(decision == "si")),
                config=config,
            )

        print("\nAgente:", result.get("final_answer", "(Sin respuesta textual)"))
        print("Pedidos:", ORDERS)


if __name__ == "__main__":
    main()
