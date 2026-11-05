
import json
import os
import re
from dataclasses import dataclass
from typing import Literal

from openai import OpenAI, OpenAIError


# ==========================================
# 1. CLIENTES DE AZURE OPENAI
# ==========================================

def azure_client(endpoint: str, api_key: str):
    return OpenAI(
        base_url=endpoint.rstrip("/") + "/openai/v1/",
        api_key=api_key,
    )


responses_client = azure_client(
    os.environ["AZURE_OPENAI_ENDPOINT"],
    os.environ["AZURE_OPENAI_API_KEY"],
)

decisions_client = azure_client(
    os.getenv(
        "AZURE_OPENAI_DECISIONS_ENDPOINT",
        os.environ["AZURE_OPENAI_ENDPOINT"],
    ),
    os.getenv(
        "AZURE_OPENAI_DECISIONS_API_KEY",
        os.environ["AZURE_OPENAI_API_KEY"],
    ),
)

RESPONSE_MODEL = os.environ[
    "AZURE_OPENAI_RESPONSES_DEPLOYMENT"
]

DECISION_MODEL = os.environ[
    "AZURE_OPENAI_DECISIONS_DEPLOYMENT"
]


# ==========================================
# 2. ESTRUCTURAS DEL PATRÓN
# ==========================================

@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class Decision:
    action: Literal["pass", "modify", "deny"]
    reason: str = ""
    updated_args: dict | None = None


# ==========================================
# 3. HOOKS DETERMINISTAS
# ==========================================

def tool_allowlist(call: ToolCall) -> Decision:
    if call.name != "send_email":
        return Decision("deny", "Herramienta no permitida")

    required = {"to", "subject", "body"}

    if (
        set(call.args) != required
        or any(
            not isinstance(call.args[k], str)
            for k in required
        )
    ):
        return Decision("deny", "Argumentos inválidos")

    return Decision("pass")


def recipient_guard(call: ToolCall) -> Decision:
    recipient = call.args["to"].strip().lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+", recipient):
        return Decision("deny", "Correo inválido")

    domain = recipient.rsplit("@", 1)[1]
    allowed = {"empresa.com", "proveedor.com"}

    if domain not in allowed:
        return Decision("deny", "Dominio no autorizado")

    return Decision("pass")


# ==========================================
# 4. HOOK INTELIGENTE: DECISIONS API
# ==========================================

def ai_decisions_guard(call: ToolCall) -> Decision:

    # Los argumentos de la herramienta son
    # la evidencia que evaluará el modelo.
    evidence = json.dumps(
        {
            "tool": call.name,
            "recipient": call.args["to"],
            "subject": call.args["subject"],
            "body": call.args["body"],
        },
        ensure_ascii=False,
    )

    try:
        result = decisions_client.decisions.create(
            model=DECISION_MODEL,
            input=evidence,
            questions=[
                {
                    "type": "predicate",
                    "name": "sensitive_content",
                    "instructions": (
                        "Does this email disclose credentials, "
                        "passwords, API keys, personal information "
                        "or restricted company information? "
                        "Evaluate the meaning of the content, "
                        "not just individual keywords."
                    ),
                },
                {
                    "type": "choice",
                    "name": "communication_type",
                    "instructions": (
                        "Classify the business email according "
                        "to its content and disclosure risk."
                    ),
                    "choices": [
                        {
                            "value": "routine",
                            "description": (
                                "Ordinary business communication "
                                "without restricted information."
                            ),
                        },
                        {
                            "value": "sensitive",
                            "description": (
                                "Communication involving sensitive "
                                "or restricted information."
                            ),
                        },
                        {
                            "value": "unclear",
                            "description": (
                                "Insufficient context to determine "
                                "whether disclosure is appropriate."
                            ),
                        },
                    ],
                },
            ],
        )
    except OpenAIError:
        return Decision(
            "deny",
            "No fue posible completar la evaluación de IA",
        )

    answers = {
        answer.name: answer
        for answer in result.answers
        if answer.name is not None
    }

    sensitive = answers.get("sensitive_content")
    category = answers.get("communication_type")

    # Fail closed: nunca interpretar rechazo,
    # respuesta ausente o error como permiso.
    if (
        sensitive is None
        or category is None
        or sensitive.type != "predicate"
        or category.type != "choice"
    ):
        return Decision(
            "deny",
            "Evaluación incompleta: requiere revisión",
        )

    probability = sensitive.probability
    confidence = category.confidence

    if probability is None or confidence is None:
        return Decision(
            "deny",
            "Evaluación sin indicadores suficientes",
        )

    print(f"[AI] Riesgo sensible: {probability:.2f}")
    print(
        f"[AI] Categoría: {category.choice} "
        f"(confianza: {confidence:.2f})"
    )

    # Umbrales ilustrativos, no calibrados.
    if probability >= 0.25:
        return Decision(
            "deny",
            "Posible información sensible: revisión requerida",
        )

    if confidence < 0.80:
        return Decision(
            "deny",
            "Clasificación incierta: revisión requerida",
        )

    if category.choice != "routine":
        return Decision(
            "deny",
            "Comunicación no clasificada como rutinaria",
        )

    return Decision("pass")


# ==========================================
# 5. HOOK DE MODIFICACIÓN
# ==========================================

def add_signature(call: ToolCall) -> Decision:
    updated = call.args.copy()
    updated["body"] += "\n\nSaludos,\nEquipo empresarial"

    return Decision(
        action="modify",
        updated_args=updated,
    )


# ==========================================
# 6. HOOK DE APROBACIÓN HUMANA
# ==========================================

def human_approval(call: ToolCall) -> Decision:
    print("\n--- CORREO PROPUESTO ---")
    print("Para:", call.args["to"])
    print("Asunto:", call.args["subject"])
    print("Mensaje:", call.args["body"])

    answer = input("\n¿Autorizar envío? (s/n): ")

    if answer.strip().lower() != "s":
        return Decision("deny", "Envío no aprobado")

    return Decision("pass")


# ==========================================
# 7. TOOL SIMULADA
# ==========================================

def execute_tool(call: ToolCall) -> dict:
    print("\n[TOOL] Envío simulado correctamente")

    return {
        "status": "simulated",
        "recipient": call.args["to"],
        "message": "Simulación completada; no se envió correo",
    }


# ==========================================
# 8. HARNESS: CADENA DE RESPONSABILIDAD
# ==========================================

HOOKS = [
    tool_allowlist,
    recipient_guard,
    ai_decisions_guard,
    add_signature,
    human_approval,
]


def run_chain(call: ToolCall) -> dict:

    for hook in HOOKS:
        decision = hook(call)
        print(f"[{hook.__name__}] {decision.action}")

        if decision.action == "deny":
            return {
                "is_error": True,
                "reason": decision.reason,
                "blocked_by": hook.__name__,
            }

        if decision.action == "modify":
            if decision.updated_args is None:
                return {
                    "is_error": True,
                    "reason": "Modificación inválida",
                }
            call.args = decision.updated_args

    return execute_tool(call)


# ==========================================
# 9. DEFINICIÓN DE HERRAMIENTA
# ==========================================

TOOLS = [
    {
        "type": "function",
        "name": "send_email",
        "description": "Envía un correo empresarial",
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


# ==========================================
# 10. AGENTE CON RESPONSES API
# ==========================================

def run_agent(user_message: str):

    response = responses_client.responses.create(
        model=RESPONSE_MODEL,
        instructions=(
            "Eres un asistente de correo empresarial. "
            "Usa send_email para preparar envíos. "
            "No afirmes que se envió un correo si "
            "la herramienta fue bloqueada o simulada."
        ),
        input=user_message,
        tools=TOOLS,
        tool_choice="required",
        parallel_tool_calls=False,
    )

    outputs = []

    for item in response.output:
        if item.type != "function_call":
            continue

        try:
            args = json.loads(item.arguments)

            if not isinstance(args, dict):
                raise ValueError("Argumentos no válidos")

            call = ToolCall(
                name=item.name,
                args=args,
            )
            result = run_chain(call)

        except (ValueError, TypeError) as exc:
            result = {
                "is_error": True,
                "reason": str(exc),
            }

        outputs.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": json.dumps(result),
        })

    if not outputs:
        print(response.output_text)
        return

    final = responses_client.responses.create(
        model=RESPONSE_MODEL,
        previous_response_id=response.id,
        input=outputs,
        instructions=(
            "Explica en español el resultado real de "
            "la herramienta. No afirmes que se ha "
            "enviado un correo si fue una simulación."
        ),
    )

    print("\nRespuesta del agente:")
    print(final.output_text)


# ==========================================
# 11. EJECUCIÓN
# ==========================================

if __name__ == "__main__":
    run_agent(
        "Envía un correo a contacto@proveedor.com "
        "confirmando la reunión del viernes a las 10 AM."
    )
