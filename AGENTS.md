# AGENTS.md

Colección didáctica de scripts de Python (comentarios, prompts y salida en español) que implementan patrones de diseño GoF aplicados al *agent loop* de un agente LLM. Los ejemplos viven en `the_agent_loop/` y cada archivo es un script independiente. En la raíz está el harness: gate, hooks y CI.

## Ejecutar los ejemplos

Desde `the_agent_loop/` (el `.venv` está ahí, creado con uv e ignorado por git):

```
uv venv && .venv\Scripts\activate
uv pip install -r ../requirements-dev.txt   # incluye requirements.txt
copy .env.template .env      # y rellenar credenciales
python 1-09-00-composite-pattern.py
```

- Los scripts ejecutan su lógica **a nivel de módulo** y llaman a Azure al ejecutarse. Los nombres con guiones no son módulos importables.
- `1-08-00` y `1-08-01` levantan FastAPI con `uvicorn.run(app)` dentro del propio archivo (`POST /chat` con SSE); `uvicorn archivo:app` no funciona.
- Solo `1-08-02-iterator-pattern-caso-de-uso.py` corre sin credenciales de Azure.
- `requirements.txt` está incompleto: `1-09-02` además necesita `requests` y `azure-search-documents`.

## Convención de nombres

`1-NN-MM-<patrón>[-variante].py`: `NN` = patrón (01 game loop, 02 update method, 03 state, 04 template method, 05 chain of responsibility, 06 interpreter, 07 memento, 08 iterator, 09 composite); `MM` = variante: `00` Python plano, `01` misma idea en LangGraph, `02`+ caso de uso. Un patrón nuevo se añade como el par `00` + `01` (y luego casos de uso), sin modificar los anteriores.

## Arquitectura compartida

- **Cliente**: siempre `openai.OpenAI(base_url=AZURE_OPENAI_ENDPOINT.rstrip("/") + "/", api_key=...)` contra un endpoint de Azure AI Foundry que termina en `/openai/v1`; no se usa `AzureOpenAI`. Cada script reconstruye su cliente.
- **Responses API** (`client.responses.create`), no Chat Completions. Loop base (`1-01`): llamar al modelo → recoger `function_call` de `response.output` → ejecutar la herramienta → devolver `function_call_output` con `previous_response_id`, con tope `max_turns`. 1-02…1-05 enriquecen ese loop.
- **Decisions API** (`client.decisions.create`, solo `1-05-01` y `1-05-02`): clasificador usado como hook de la cadena; requiere `AZURE_OPENAI_DECISIONS_DEPLOYMENT` (solo `gpt-6-luna`). Los hooks fallan **cerrado**: error o respuesta ausente ⇒ `deny`.
- **LangGraph** (`1-NN-01-*`, `1-05-02`, `1-09-02`): estado `TypedDict` + `StateGraph`; `InMemorySaver` por `thread_id`; `interrupt`/`Command` para aprobación humana.
- **Composite (`1-09-*`)**: `Block`/`Searcher` con hojas y `Composite`; en `1-09-02` cada `Composite` captura excepciones de sus hijos en `errors` para que una fuente caída no tumbe el resto.

## Variables de entorno

`.env` está en `.gitignore`; `.env.template` sí se versiona: al introducir una variable nueva, añádela al template. Obligatorias en todo script con LLM: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`. El resto está documentado en el template.

## Definición de terminado

1. `python scripts/gate.py` en verde (lint, formato, tipos y tests). Si falla, corrige y repite.
2. Revisión independiente (otro agente o una persona) contra la spec de la feature (`specs/features/NN-nombre/`) o, si no hay feature, contra lo pedido, con el diff y la salida del gate. Responde `accept`, `revise` o `block`. Solo `accept` cierra la tarea; `revise` admite 2 vueltas; con `block` o a la tercera vuelta, para y pregunta.
3. Reporta las comprobaciones ejecutadas y su resultado.

## Specs y continuidad

- Método SDD en `specs/orden_spec.md`; cada feature vive en `specs/features/NN-nombre/`, copiada de `_plantilla/`.
- Al empezar una sesión: lee `specs/progress.md`, mira `git log --oneline -10` y ejecuta el gate antes de tocar nada. Al terminar, actualiza `specs/progress.md`.
- Lo terminado lo registra git. Un error que se repite se convierte en una línea de este archivo, en una skill o, si puede costar datos, dinero o seguridad, en un hook o una regla del gate (`specs/orden_spec.md` §8).

## Harness

- Qué revisa el gate (rutas, reglas, umbrales) está en `pyproject.toml`. `scripts/gate.py`, `.claude/` y `.github/workflows/` se copian igual a otros proyectos.
- Dependencias: `requirements.txt` para ejecutar y `requirements-dev.txt` (la incluye) para el gate.
- `tests/test_harness.py` prueba que los hooks bloquean lo que prometen.
