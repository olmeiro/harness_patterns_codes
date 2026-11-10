import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

load_dotenv()


# 1. Cliente de Azure OpenAI
client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # el .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
)

MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# 2. Estado del agente
class EditorState(TypedDict):
    document: str
    messages: list[dict]
    instruction: str


# 3. Nodo que modifica el documento
def editar_documento(state: EditorState):
    user_message = {
        "role": "user",
        "content": (
            f"Documento actual:\n{state['document']}\n\nInstrucción:\n{state['instruction']}"
        ),
    }

    response = client.responses.create(
        model=MODEL,
        instructions=(
            "Eres un editor de Markdown. "
            "Devuelve únicamente el documento completo "
            "actualizado, sin explicaciones ni bloques de código."
        ),
        input=state["messages"] + [user_message],
    )

    nuevo_documento = response.output_text

    if not nuevo_documento.strip():
        raise ValueError("El modelo no devolvió contenido")

    return {
        "document": nuevo_documento,
        "messages": state["messages"]
        + [
            user_message,
            {"role": "assistant", "content": nuevo_documento},
        ],
    }


# 4. Construir LangGraph
builder = StateGraph(EditorState)

builder.add_node("editar_documento", editar_documento)
builder.add_edge(START, "editar_documento")
builder.add_edge("editar_documento", END)

# Memento: checkpoints automáticos
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "sesion-editor-1"}}


# 5. Archivo de trabajo
file_path = Path("plan.md")
file_path.write_text("# Plan del proyecto\n", encoding="utf-8")


def guardar_archivo(state):
    file_path.write_text(state["document"], encoding="utf-8")


# 6. Turno 1
resultado = graph.invoke(
    {
        "document": file_path.read_text(encoding="utf-8"),
        "messages": [],
        "instruction": "Agrega una sección de objetivos.",
    },
    config,
)

guardar_archivo(resultado)

# Guardamos la referencia al checkpoint del turno 1
checkpoint_1 = graph.get_state(config)


# 7. Turno 2
resultado = graph.invoke(
    {"instruction": ("Reemplaza todo el documento por una propuesta diferente.")},
    config,
)

guardar_archivo(resultado)

print("Documento después del turno 2:")
print(file_path.read_text(encoding="utf-8"))


# 8. REWIND: volver al estado del turno 1

# Crear una rama desde el checkpoint anterior
restored_config = graph.update_state(
    checkpoint_1.config,
    values={
        "document": checkpoint_1.values["document"],
        "messages": checkpoint_1.values["messages"],
    },
    as_node="editar_documento",
)

# Recuperar el estado restaurado
restored_state = graph.get_state(restored_config)

# Restaurar también el archivo físico
guardar_archivo(restored_state.values)

print("\nDocumento restaurado:")
print(file_path.read_text(encoding="utf-8"))
