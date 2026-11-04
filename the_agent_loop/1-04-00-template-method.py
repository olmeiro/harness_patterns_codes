
import os
import json
from typing import final

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ==========================================
# 1. HERRAMIENTA DE EJEMPLO
# ==========================================

def consultar_factura(factura_id: str) -> dict:
    """Consulta una factura en una base de datos simulada."""

    facturas = {
        "FAC-001": {
            "factura_id": "FAC-001",
            "estado": "Pendiente",
            "valor": 150000,
            "nota_interna": "Cliente en seguimiento",
        }
    }

    return facturas.get(
        factura_id,
        {"error": "Factura no encontrada"}
    )


# ==========================================
# 2. CLASE BASE - TEMPLATE METHOD
# ==========================================

class BaseAgent:

    def __init__(self, client, model, tool_handlers):
        self.client = client
        self.model = model
        self.tool_handlers = tool_handlers
        self.transcript = []

    # HOOK 1: Instrucciones
    def system_prompt(self):
        return "Eres un asistente empresarial."

    # HOOK 2: Selección de herramientas
    def select_tools(self):
        return []

    # HOOK 3: Procesamiento de resultados
    def on_tool_result(self, name, result):
        return result

    # TEMPLATE METHOD: Flujo fijo
    @final
    def run_turn(self, user_message):

        inputs = [
            {"role": "user", "content": user_message}
        ]

        previous_id = None

        # Límite de rondas del agente
        for _ in range(5):

            # 1. Preparar la solicitud
            request = {
                "model": self.model,
                "instructions": self.system_prompt(),
                "input": inputs,
                "tools": self.select_tools(),
            }

            if previous_id:
                request["previous_response_id"] = previous_id

            # 2. Llamar a Azure OpenAI
            response = self.client.responses.create(
                **request
            )

            if response.status == "incomplete":
                raise RuntimeError(
                    "La respuesta del modelo está incompleta"
                )

            # 3. Identificar llamadas a herramientas
            calls = [
                item for item in response.output
                if item.type == "function_call"
            ]

            tool_outputs = []

            for call in calls:

                handler = self.tool_handlers.get(call.name)

                if handler is None:
                    raise ValueError(
                        f"Herramienta no permitida: {call.name}"
                    )

                # 4. Ejecutar herramienta
                args = json.loads(call.arguments)
                result = handler(**args)

                # Hook para personalizar el resultado
                result = self.on_tool_result(
                    call.name, result
                )

                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result),
                })

            # 5. Registrar la ejecución
            self.transcript.append({
                "response_id": response.id,
                "tools": [call.name for call in calls],
                "tokens": (
                    response.usage.total_tokens
                    if response.usage else None
                ),
            })

            # Si no hay herramientas, finalizar
            if not calls:
                return response.output_text

            # Continuar con los resultados de las tools
            inputs = tool_outputs
            previous_id = response.id

        raise RuntimeError(
            "Se alcanzó el límite de rondas del agente"
        )


# ==========================================
# 3. AGENTE ESPECIALIZADO
# ==========================================

class FinanceAgent(BaseAgent):

    def system_prompt(self):
        return (
            "Eres un agente financiero empresarial. "
            "Consulta las facturas usando las herramientas "
            "disponibles y responde en español."
        )

    def select_tools(self):
        return [
            {
                "type": "function",
                "name": "consultar_factura",
                "description": "Consulta el estado de una factura",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "factura_id": {
                            "type": "string",
                            "description": "ID de la factura",
                        }
                    },
                    "required": ["factura_id"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
        ]

    def on_tool_result(self, name, result):
        # Eliminar información interna
        return {
            k: v for k, v in result.items()
            if k != "nota_interna"
        }


# ==========================================
# 4. EJECUCIÓN
# ==========================================

client = OpenAI(
    base_url=(
        f"{os.environ['AZURE_OPENAI_ENDPOINT'].rstrip('/')}"
        "/openai/v1/"
    ),
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)

agent = FinanceAgent(
    client=client,
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    tool_handlers={
        "consultar_factura": consultar_factura
    },
)

respuesta = agent.run_turn(
    "¿Cuál es el estado de la factura FAC-001?"
)

print("RESPUESTA:", respuesta)
print("TRANSCRIPT:", agent.transcript)
