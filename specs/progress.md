# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Revisor de CI en `main` (PR #1): `.github/workflows/revisor.yml` + `scripts/revisor_ci.py` con `gpt-5.2`. Gate verde en CI (29 tests), ya sin el aviso de Node 20. `revisor` comprobado de punta a punta en el PR #2: llama a Azure, lee el veredicto y falla cerrado. Constitución sin llenar (`/specs init` pendiente).

## Siguiente paso

Añadir `revisor` como required check en el ruleset de `main`.

## Bloqueos

- El deny `**/.env.*` de `.claude/settings.json` impide a los agentes leer y editar `the_agent_loop/.env.template`, que AGENTS.md pide mantener al día. Por eso las variables `AZURE_OPENAI_EVALUATOR_*` se añadieron a mano. Decidir si se exceptúa el template.

## Registro de sesiones

2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — mergeado (PR #1) y probado en CI (PR #2).
