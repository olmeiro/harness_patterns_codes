
import os
import json
from dataclasses import dataclass
from typing import Literal
from openai import OpenAI


# =====================================
# 1. CLIENTE AZURE OPENAI
# =====================================

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    base_url=(
        os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        + "/openai/v1/"
    ),
)

MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# =====================================
# 2. ESTRUCTURAS DEL PATRÓN
# =====================================

@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class Decision:
    action: Literal["pass", "modify", "deny"]
    reason: str = ""
    updated_args: dict | None = None


# =====================================
# 3. HOOKS: CHAIN OF RESPONSIBILITY
# =====================================

def tool_allowlist(call: ToolCall) -> Decision:
    """Verifica que la herramienta esté autorizada."""

    if call.name != "send_email":
        return Decision("deny", "Herramienta prohibida")

    return Decision("pass")


def recipient_guard(call: ToolCall) -> Decision:
    """Verifica el dominio del destinatario."""

    recipient = call.args.get("to", "")

    if not isinstance(recipient, str):
        return Decision("deny", "Destinatario inválido")

    parts = recipient.strip().lower().split("@")

    allowed_domains = {"empresa.com", "proveedor.com"}

    if (
        len(parts) != 2
        or not parts[0]
        or parts[1] not in allowed_domains
    ):
        return Decision("deny", "Destinatario no autorizado")

    return Decision("pass")


def sensitive_data_scanner(call: ToolCall) -> Decision:
    """Detecta palabras sensibles (demostración)."""

    body = call.args.get("body", "")

    if not isinstance(body, str):
        return Decision("deny", "Contenido inválido")

    forbidden = ["password", "api_key", "confidencial"]

    if any(word in body.lower() for word in forbidden):
        return Decision("deny", "Información sensible detectada")

    return Decision("pass")


def add_signature(call: ToolCall) -> Decision:
    """Modifica el contenido agregando una firma."""

    updated = call.args.copy()
    updated["body"] += "\n\nSaludos,\nEquipo empresarial"

    return Decision(
        action="modify",
        updated_args=updated,
    )


def human_approval(call: ToolCall) -> Decision:
    """Solicita confirmación antes de ejecutar."""

    print("\nCorreo propuesto:")
    print("Destinatario:", call.args["to"])
    print("Asunto:", call.args["subject"])
    print("Contenido:", call.args["body"])

    answer = input("\n¿Aprobar envío? (s/n): ")

    if answer.strip().lower() != "s":
        return Decision("deny", "Usuario rechazó el envío")

    return Decision("pass")


# =====================================
# 4. HERRAMIENTA REAL (SIMULADA)
# =====================================

def execute_tool(call: ToolCall) -> dict:
    """Simula el envío; no envía correos reales."""

    print("\n[TOOL] Simulando envío de correo...")

    return {
        "status": "simulated",
        "recipient": call.args["to"],
        "message": "Correo simulado correctamente",
    }


# =====================================
# 5. HARNESS: EJECUTOR DE LA CADENA
# =====================================

HOOKS = [
    tool_allowlist,
    recipient_guard,
    sensitive_data_scanner,
    add_signature,
    human_approval,
]


def run_chain(call: ToolCall) -> dict:

    for hook in HOOKS:
        decision = hook(call)

        # Auditoría de cada decisión
        print(f"[{hook.__name__}] {decision.action}")

        if decision.action == "deny":
            return {
                "is_error": True,
                "hook": hook.__name__,
                "message": decision.reason,
            }

        if decision.action == "modify":
            if decision.updated_args is None:
                return {
                    "is_error": True,
                    "message": "Modificación inválida",
                }

            call.args = decision.updated_args

    # Solo se ejecuta si ningún hook bloqueó la llamada
    return execute_tool(call)


# =====================================
# 6. DECLARACIÓN DE LA TOOL
# =====================================

TOOLS = [
    {
        "type": "function",
        "name": "send_email",
        "description": "Envía un correo electrónico empresarial",
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
    }
]


# =====================================
# 7. RESPONSES API + CHAIN
# =====================================

def run_agent(user_message: str):

    response = client.responses.create(
        model=MODEL,
        instructions=(
            "Eres un asistente de correo empresarial. "
            "Utiliza send_email cuando el usuario solicite "
            "enviar un correo. Nunca afirmes que un correo "
            "fue enviado si la herramienta fue bloqueada "
            "o si su resultado indica una simulación."
        ),
        input=user_message,
        tools=TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
    )

    tool_outputs = []

    for item in response.output:

        if item.type != "function_call":
            continue

        try:
            args = json.loads(item.arguments)

            if not isinstance(args, dict):
                raise ValueError("Argumentos inválidos")

            call = ToolCall(name=item.name, args=args)
            result = run_chain(call)

        except (ValueError, TypeError) as exc:
            result = {
                "is_error": True,
                "message": str(exc),
            }

        tool_outputs.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result),
        })

    if not tool_outputs:
        print(response.output_text)
        return

    final_response = client.responses.create(
        model=MODEL,
        previous_response_id=response.id,
        input=tool_outputs,
    )

    print("\nRespuesta del agente:")
    print(final_response.output_text)


# =====================================
# 8. EJECUCIÓN
# =====================================

if __name__ == "__main__":

    run_agent(
        "Envía un correo a contacto@proveedor.com "
        "con asunto 'Reunión' indicando que "
        "confirmamos la reunión del viernes."
    )
