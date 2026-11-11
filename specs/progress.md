# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Revisor de CI obligatorio en `main`; confirmación para commits/push mergeada (PR #3, con bypass: el revisor con `gpt-5.2` pedía `revise` por detalles menores). Rama `feat/revisor-decisions`: el revisor de CI pasa a la Decisions API (`gpt-6-luna`), con un filtro determinista y la decisión tomada en el código; revisor local `accept` en la vuelta 2, gate verde (62 tests); sin commitear ni probar contra la API real. Plantilla `harness-python` sin publicar y sin este cambio. Constitución sin llenar.

## Siguiente paso

Probar `scripts/revisor_ci.py` en local contra la API; `.env.template` a `gpt-6-luna`; PR (último bypass); tras el merge, variable del repo `AZURE_OPENAI_EVALUATOR_DEPLOYMENT` = `gpt-6-luna` y PR de prueba. Luego migrar a `harness-python` y `/specs init`.

## Bloqueos

Ninguno.

## Registro de sesiones

2026-11-11 — revisor de CI con Decisions API — accept local; pendientes prueba real y PR.
2026-11-11 — confirmación obligatoria para commits/push y plantilla `harness-python` — mergeado (PR #3).
2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — mergeado (PR #1) y probado en CI (PR #2).
