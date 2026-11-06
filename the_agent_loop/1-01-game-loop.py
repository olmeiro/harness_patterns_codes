
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Cliente Azure OpenAI
client = OpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

# Herramienta disponible para el agente
def get_order_status(order_id: str) -> dict:
    return {
        "order_id": order_id,
        "status": "En preparación"
    }


tools = [
    {
        "type": "function",
        "name": "get_order_status",
        "description": "Consulta el estado de un pedido.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"}
            },
            "required": ["order_id"],
            "additionalProperties": False
        },
        "strict": True
    }
]


def agent_loop(user_input: str, max_turns: int = 5):
    turn = 0
    previous_response_id = None
    pending_input = user_input

    while turn < max_turns:
        turn += 1

        # 1. Consultar el modelo
        request = {
            "model": deployment,
            "instructions": "Eres un asistente de pedidos.",
            "input": pending_input,
            "tools": tools,
        }

        if previous_response_id is not None:
            request["previous_response_id"] = previous_response_id

        response = client.responses.create(**request)

        # 2. Comprobar si la respuesta está incompleta
        if response.status != "completed":
            raise RuntimeError(
                f"Respuesta no completada: {response.status}"
            )

        # 3. Identificar solicitudes de herramientas
        calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        # 4. Finalizar si no hay herramientas pendientes
        if not calls:
            return response.output_text

        # 5. Ejecutar herramientas
        tool_results = []

        for call in calls:
            if call.name != "get_order_status":
                raise ValueError("Herramienta no permitida")

            args = json.loads(call.arguments)

            result = get_order_status(
                order_id=args["order_id"]
            )

            tool_results.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": json.dumps(result)
            })

        # 6. Preparar la siguiente iteración
        previous_response_id = response.id
        pending_input = tool_results

    raise RuntimeError("Se alcanzó max_turns")


# Ejecutar el agente
answer = agent_loop(
    "¿Cuál es el estado del pedido 123?"
)

print(answer)
