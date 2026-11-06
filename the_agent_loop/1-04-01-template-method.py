# Implementacion en LangGraph del patrón Template Method para agentes conversacionales.
import os
import json
from typing import final

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
    AIMessage,
)
from langgraph.graph import (
    StateGraph,
    MessagesState,
    START,
    END,
)

load_dotenv()


# ==========================================
# 1. HERRAMIENTA FINANCIERA
# ==========================================

@tool
def consultar_factura(factura_id: str) -> dict:
    """Consulta una factura por su identificador."""

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
# 2. ESTADO COMPARTIDO
# ==========================================

class AgentState(MessagesState):
    transcript: list[dict]


# ==========================================
# 3. CLASE BASE - TEMPLATE METHOD
# ==========================================

class BaseAgent:

    def __init__(self, llm):
        self.llm = llm

        # Herramientas permitidas por la subclase
        tools = self.select_tools()

        self.tools = {
            tool.name: tool for tool in tools
        }

        self.model = (
            llm.bind_tools(tools)
            if tools else llm
        )

        # Grafo compartido
        self.graph = self._build_graph()

    # HOOK 1: Prompt
    def system_prompt(self):
        return "Eres un asistente empresarial."

    # HOOK 2: Herramientas
    def select_tools(self):
        return []

    # HOOK 3: Resultados
    def on_tool_result(self, name, result):
        return result

    # NODO 1: Llamada al modelo
    def _call_model(self, state: AgentState):

        messages = [
            SystemMessage(content=self.system_prompt()),
            *state["messages"],
        ]

        response = self.model.invoke(messages)

        return {"messages": [response]}

    # NODO 2: Ejecutar herramientas
    def _run_tools(self, state: AgentState):

        last_message = state["messages"][-1]
        outputs = []

        for call in last_message.tool_calls:

            name = call["name"]

            if name not in self.tools:
                raise ValueError(
                    f"Herramienta no autorizada: {name}"
                )

            # Ejecutar herramienta
            result = self.tools[name].invoke(
                call["args"]
            )

            # Aplicar hook especializado
            result = self.on_tool_result(
                name, result
            )

            outputs.append(
                ToolMessage(
                    content=json.dumps(
                        result, ensure_ascii=False
                    ),
                    tool_call_id=call["id"],
                    name=name,
                )
            )

        return {"messages": outputs}

    # ENRUTAMIENTO FIJO
    def _route(self, state: AgentState):

        last_message = state["messages"][-1]

        if last_message.tool_calls:
            return "tools"

        return "finish"

    # NODO 3: Registrar turno
    def _record(self, state: AgentState):

        record = {
            "llm_calls": sum(
                isinstance(m, AIMessage)
                for m in state["messages"]
            ),
            "tools_used": [
                m.name
                for m in state["messages"]
                if isinstance(m, ToolMessage)
            ],
        }

        return {
            "transcript": (
                state.get("transcript", []) + [record]
            )
        }

    # TEMPLATE METHOD: GRAFO FIJO
    @final
    def _build_graph(self):

        graph = StateGraph(AgentState)

        graph.add_node(
            "call_model", self._call_model
        )
        graph.add_node(
            "run_tools", self._run_tools
        )
        graph.add_node(
            "record", self._record
        )

        graph.add_edge(START, "call_model")

        graph.add_conditional_edges(
            "call_model",
            self._route,
            {
                "tools": "run_tools",
                "finish": "record",
            },
        )

        graph.add_edge(
            "run_tools", "call_model"
        )
        graph.add_edge("record", END)

        return graph.compile()

    # PUNTO DE ENTRADA FIJO
    @final
    def run_turn(self, question: str):

        return self.graph.invoke(
            {
                "messages": [
                    HumanMessage(content=question)
                ],
                "transcript": [],
            },
            config={"recursion_limit": 12},
        )


# ==========================================
# 4. AGENTE ESPECIALIZADO
# ==========================================

class FinanceAgent(BaseAgent):

    def system_prompt(self):
        return (
            "Eres un agente financiero. "
            "Consulta las facturas mediante herramientas. "
            "Responde en español y no inventes datos."
        )

    def select_tools(self):
        return [consultar_factura]

    def on_tool_result(self, name, result):
        # Eliminar campos internos
        if name == "consultar_factura":
            result = {
                k: v for k, v in result.items()
                if k != "nota_interna"
            }

        return result


# ==========================================
# 5. CONFIGURACIÓN AZURE OPENAI
# ==========================================

llm = ChatOpenAI(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    base_url=(
        os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        + "/"
    ),
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    use_responses_api=True,
)


# ==========================================
# 6. EJECUCIÓN
# ==========================================

agent = FinanceAgent(llm)

result = agent.run_turn(
    "¿Cuál es el estado de la factura FAC-001?"
)

print("RESPUESTA:")
print(result["messages"][-1].text)

print("\nTRANSCRIPT:")
print(json.dumps(
    result["transcript"],
    indent=2,
    ensure_ascii=False,
))
