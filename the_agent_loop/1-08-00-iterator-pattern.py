import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

# 1. Configuración de Azure OpenAI
load_dotenv()

client = AsyncOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # El .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
)

MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]

app = FastAPI(title="Patrón Iterator")


class ChatRequest(BaseModel):
    mensaje: str


# 2. ITERATOR: consumir los eventos del LLM
async def generar_eventos(mensaje: str):
    try:
        stream = await client.responses.create(
            model=MODEL,
            input=mensaje,
            stream=True,
        )

        # Aquí aplicamos el patrón Iterator
        async for evento in stream:
            if evento.type == "response.output_text.delta":
                # Reenviamos solo el fragmento recibido
                data = json.dumps(
                    {"texto": evento.delta},
                    ensure_ascii=False,
                )
                yield f"event: delta\ndata: {data}\n\n"

            elif evento.type == "response.completed":
                yield "event: done\ndata: {}\n\n"
                return

            elif evento.type in (
                "response.failed",
                "response.incomplete",
                "error",
            ):
                yield 'event: error\ndata: {"mensaje":"Generación incompleta"}\n\n'
                return

    except Exception:
        logging.exception("Error durante el streaming")
        yield 'event: error\ndata: {"mensaje":"Error al generar respuesta"}\n\n'


# 3. Endpoint FastAPI
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


# 4. Ejecutar la aplicación: python 1-08-00-iterator-pattern.py
# (el nombre del archivo no es un módulo importable, por eso no sirve "uvicorn archivo:app")
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
    # ejecutar: python 1-08-00-iterator-pattern.py


# curl -N -X POST "http://localhost:8000/chat" \
#   -H "Content-Type: application/json" \
#   -d '{"mensaje":"Explica el patrón Iterator en Python"}'
