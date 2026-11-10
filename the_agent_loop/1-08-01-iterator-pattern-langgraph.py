import json
import logging
import os
from typing import NotRequired, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

# 1. Configuración
load_dotenv()

llm = ChatOpenAI(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # El .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
    use_responses_api=True,
    output_version="responses/v1",
)

app = FastAPI(title="Iterator con LangGraph")


# 2. Estado del agente
class AgentState(TypedDict):
    pregunta: str
    respuesta: NotRequired[str]


class ChatRequest(BaseModel):
    mensaje: str = Field(min_length=1)


# 3. Nodos del grafo
def preparar(state: AgentState):
    return {"pregunta": state["pregunta"].strip()}


async def responder(state: AgentState):
    resultado = await llm.ainvoke(
        [
            ("system", "Responde en español de forma clara y breve."),
            ("human", state["pregunta"]),
        ]
    )

    return {"respuesta": resultado.text}


# 4. Construcción del grafo
builder = StateGraph(AgentState)

builder.add_node("preparar", preparar)
builder.add_node("responder", responder)

builder.add_edge(START, "preparar")
builder.add_edge("preparar", "responder")
builder.add_edge("responder", END)

graph = builder.compile()


# 5. Formatear eventos SSE
def sse(tipo: str, datos: dict):
    data = json.dumps(datos, ensure_ascii=False)
    return f"event: {tipo}\ndata: {data}\n\n"


# 6. ITERATOR: recorrer los eventos del grafo
async def generar_eventos(mensaje: str):
    try:
        async for parte in graph.astream(
            {"pregunta": mensaje},
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            # Fragmentos generados por el LLM
            if parte["type"] == "messages":
                chunk, metadata = parte["data"]

                if metadata.get("langgraph_node") == "responder":
                    texto = chunk.text
                    if texto:
                        yield sse("delta", {"texto": texto})

            # Actualizaciones del estado del grafo
            elif parte["type"] == "updates":
                for nodo in parte["data"]:
                    yield sse("nodo", {"nombre": nodo})

        yield sse("done", {})

    except Exception:
        logging.exception("Error en el grafo")
        yield sse("error", {"mensaje": "Error al ejecutar el agente"})


# 7. Endpoint FastAPI
@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        generar_eventos(request.mensaje),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# 8. Ejecutar la aplicación: python 1-08-01-iterator-pattern-langgraph.py
# (el nombre del archivo no es un módulo importable, por eso no sirve "uvicorn archivo:app")
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
