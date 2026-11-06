
import os
import json
import uuid
from typing import TypedDict

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()


# ==========================================
# 1. CLIENTES AZURE OPENAI
# ==========================================

def create_client(endpoint, key):
    return OpenAI(
        base_url=endpoint.rstrip("/") + "/",
        api_key=key,
    )


responses_client = create_client(
    os.environ["AZURE_OPENAI_ENDPOINT"],
    os.environ["AZURE_OPENAI_API_KEY"],
)

decisions_client = create_client(
    os.getenv(
        "AZURE_OPENAI_DECISIONS_ENDPOINT",
        os.environ["AZURE_OPENAI_ENDPOINT"],
    ),
    os.getenv(
        "AZURE_OPENAI_DECISIONS_API_KEY",
        os.environ["AZURE_OPENAI_API_KEY"],
    ),
)

RESPONSES_MODEL = os.getenv(
    "AZURE_OPENAI_RESPONSES_DEPLOYMENT",
    os.environ["AZURE_OPENAI_DEPLOYMENT"],
)

DECISIONS_MODEL = os.getenv(
    "AZURE_OPENAI_DECISIONS_DEPLOYMENT",
    os.environ["AZURE_OPENAI_DEPLOYMENT"],
)


# ==========================================
# 2. ESTADO COMPARTIDO DEL GRAFO
# ==========================================

class AgentState(TypedDict, total=False):
    request: str
    response_id: str
    call_id: str
    tool_name: str
    args: dict
    blocked: bool
    reason: str
    audit: list[str]
    execution: dict
    final_answer: str


# ==========================================
# 3. HERRAMIENTA PARA REGISTRAR DECISIONES
# ==========================================

def record(state, hook, action, reason="", **updates):
    entry = f"{hook}: {action}"

    if reason:
        entry += f" ({reason})"

    result = {
        "audit": state.get("audit", []) + [entry],
        "blocked": action == "deny",
    }

    if reason:
        result["reason"] = reason

    return {**result, **updates}


# ==========================================
# 4. AGENTE: RESPONSES API
# ==========================================

TOOLS = [{
    "type": "function",
    "name": "send_email",
    "description": "Preparar el envío de un correo empresarial",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
        "additionalProperties": False,
    },
    "strict": True,
}]


def propose_tool(state: AgentState):
    response = responses_client.responses.create(
        model=RESPONSES_MODEL,
        instructions=(
            "Eres un asistente empresarial de correos. "
            "Cuando el usuario solicite enviar un correo, "
            "prepara una llamada a send_email. "
            "No afirmes que el correo fue enviado."
        ),
        input=state["request"],
        tools=TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
    )

    calls = [
        item for item in response.output
        if item.type == "function_call"
    ]

    if len(calls) != 1:
        return record(
            state, "propose_tool", "deny",
            "Se esperaba exactamente una llamada",
        )

    item = calls[0]

    try:
        args = json.loads(item.arguments)
    except (ValueError, TypeError):
        args = None

    data = {
        "response_id": response.id,
        "call_id": item.call_id,
        "tool_name": item.name,
        "args": args,
    }

    if not isinstance(args, dict):
        return record(
            state, "propose_tool", "deny",
            "Argumentos inválidos",
            **data,
        )

    return record(
        state, "propose_tool", "pass", **data
    )


# ==========================================
# 5. HOOK: TOOL ALLOWLIST
# ==========================================

def tool_allowlist(state: AgentState):
    if state["tool_name"] != "send_email":
        return record(
            state, "tool_allowlist", "deny",
            "Herramienta no autorizada",
        )

    args = state["args"]
    required = {"to", "subject", "body"}

    if (
        set(args) != required
        or any(
            not isinstance(args[k], str)
            for k in required
        )
    ):
        return record(
            state, "tool_allowlist", "deny",
            "Argumentos inválidos",
        )

    return record(state, "tool_allowlist", "pass")


# ==========================================
# 6. HOOK: RECIPIENT GUARD
# ==========================================

def recipient_guard(state: AgentState):
    recipient = state["args"]["to"].strip().lower()

    parts = recipient.split("@")
    allowed_domains = {"empresa.com", "proveedor.com"}

    valid = (
        len(parts) == 2
        and bool(parts[0])
        and parts[1] in allowed_domains
        and not any(c.isspace() for c in recipient)
    )

    if not valid:
        return record(
            state, "recipient_guard", "deny",
            "Destinatario no autorizado",
        )

    return record(state, "recipient_guard", "pass")


# ==========================================
# 7. HOOK: DECISIONS API
# ==========================================

def ai_decisions_guard(state: AgentState):
    args = state["args"]

    evidence = json.dumps(
        {
            "recipient": args["to"],
            "subject": args["subject"],
            "body": args["body"],
        },
        ensure_ascii=False,
    )

    try:
        decision = decisions_client.decisions.create(
            model=DECISIONS_MODEL,
            input=evidence,
            questions=[
                {
                    "type": "predicate",
                    "name": "sensitive_content",
                    "instructions": (
                        "Does this email disclose credentials, "
                        "passwords, personal information, "
                        "or confidential company information? "
                        "Evaluate meaning, not just keywords."
                    ),
                },
                {
                    "type": "choice",
                    "name": "communication_type",
                    "instructions": (
                        "Classify the email according "
                        "to its disclosure risk."
                    ),
                    "choices": [
                        {
                            "value": "routine",
                            "description": (
                                "Ordinary business communication."
                            ),
                        },
                        {
                            "value": "sensitive",
                            "description": (
                                "Contains restricted information."
                            ),
                        },
                        {
                            "value": "unclear",
                            "description": (
                                "Insufficient context to classify."
                            ),
                        },
                    ],
                },
            ],
        )

        answers = {
            answer.name: answer
            for answer in decision.answers
            if answer.name
        }

        sensitive = answers.get("sensitive_content")
        category = answers.get("communication_type")

        if (
            sensitive is None
            or category is None
            or sensitive.type != "predicate"
            or category.type != "choice"
        ):
            raise ValueError("Evaluación incompleta")

        probability = sensitive.probability
        confidence = category.confidence

        if (
            not isinstance(probability, (int, float))
            or not isinstance(confidence, (int, float))
            or not 0 <= probability <= 1
            or not 0 <= confidence <= 1
        ):
            raise ValueError("Indicadores inválidos")

    except (OpenAIError, ValueError):
        return record(
            state, "ai_decisions_guard", "deny",
            "No se pudo verificar la seguridad",
        )

    # Umbrales de demostración
    if probability >= 0.25:
        return record(
            state, "ai_decisions_guard", "deny",
            "Posible contenido sensible",
        )

    if confidence < 0.80 or category.choice != "routine":
        return record(
            state, "ai_decisions_guard", "deny",
            "Comunicación requiere revisión",
        )

    return record(
        state, "ai_decisions_guard", "pass"
    )


# ==========================================
# 8. HOOK: MODIFY
# ==========================================

def add_signature(state: AgentState):
    updated = state["args"].copy()

    updated["body"] += (
        "\n\nSaludos,\nEquipo empresarial"
    )

    return record(
        state, "add_signature", "modify",
        args=updated,
    )


# ==========================================
# 9. HOOK: HUMAN APPROVAL
# ==========================================

def human_approval(state: AgentState):

    # LangGraph guarda el estado y pausa el grafo
    approved = interrupt({
        "question": "¿Autoriza este correo?",
        "email": state["args"],
    })

    if approved is not True:
        return record(
            state, "human_approval", "deny",
            "El usuario rechazó el correo",
        )

    return record(state, "human_approval", "pass")


# ==========================================
# 10. EJECUCIÓN DE LA HERRAMIENTA
# ==========================================

def execute_tool(state: AgentState):
    # Simulación: no se envía un correo real.
    return {
        "execution": {
            "status": "simulated",
            "recipient": state["args"]["to"],
            "message": "Envío simulado correctamente",
        },
        "audit": state.get("audit", [])
                 + ["execute_tool: simulated"],
    }


# ==========================================
# 11. RESPUESTA FINAL DEL AGENTE
# ==========================================

def finalize(state: AgentState):

    if state.get("blocked"):
        result = {
            "is_error": True,
            "reason": state.get("reason", "Operación bloqueada"),
        }
    else:
        result = state["execution"]

    # Si no hubo function_call válido
    if not state.get("call_id"):
        return {
            "final_answer": result.get(
                "reason", "No se pudo preparar la herramienta"
            )
        }

    response = responses_client.responses.create(
        model=RESPONSES_MODEL,
        previous_response_id=state["response_id"],
        input=[{
            "type": "function_call_output",
            "call_id": state["call_id"],
            "output": json.dumps(result),
        }],
        instructions=(
            "Explica en español el resultado de la operación. "
            "Si fue bloqueada, explica el motivo. "
            "Si fue simulada, aclara que no se envió "
            "ningún correo real."
        ),
    )

    return {"final_answer": response.output_text}


# ==========================================
# 12. ROUTER DEL PATRÓN
# ==========================================

def route(state: AgentState):
    if state.get("blocked", False):
        return "blocked"

    return "continue"


# ==========================================
# 13. CONSTRUCCIÓN DE LANGGRAPH
# ==========================================

builder = StateGraph(AgentState)

builder.add_node("propose_tool", propose_tool)
builder.add_node("tool_allowlist", tool_allowlist)
builder.add_node("recipient_guard", recipient_guard)
builder.add_node("ai_decisions_guard", ai_decisions_guard)
builder.add_node("add_signature", add_signature)
builder.add_node("human_approval", human_approval)
builder.add_node("execute_tool", execute_tool)
builder.add_node("finalize", finalize)

builder.add_edge(START, "propose_tool")

chain = [
    ("propose_tool", "tool_allowlist"),
    ("tool_allowlist", "recipient_guard"),
    ("recipient_guard", "ai_decisions_guard"),
    ("ai_decisions_guard", "add_signature"),
    ("add_signature", "human_approval"),
    ("human_approval", "execute_tool"),
]

for current, next_node in chain:
    builder.add_conditional_edges(
        current,
        route,
        {
            "continue": next_node,
            "blocked": "finalize",
        },
    )

builder.add_edge("execute_tool", "finalize")
builder.add_edge("finalize", END)

graph = builder.compile(
    checkpointer=InMemorySaver()
)


# ==========================================
# 14. EJECUCIÓN Y APROBACIÓN
# ==========================================

if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }

    result = graph.invoke(
        {
            "request": (
                "Envía un correo a contacto@proveedor.com "
                "confirmando la reunión del viernes "
                "a las 10 AM."
            ),
            "audit": [],
        },
        config=config,
    )

    # Si LangGraph solicitó aprobación
    if "__interrupt__" in result:

        request = result["__interrupt__"][0].value

        print("\nSolicitud de aprobación:")
        print(json.dumps(request, indent=2, ensure_ascii=False))

        answer = input("\n¿Aprobar envío? (s/n): ")

        approved = answer.strip().lower() == "s"

        # Reanudar el mismo thread
        result = graph.invoke(
            Command(resume=approved),
            config=config,
        )

    print("\nAUDITORÍA:")
    for entry in result.get("audit", []):
        print("-", entry)

    print("\nRESPUESTA FINAL:")
    print(result["final_answer"])
