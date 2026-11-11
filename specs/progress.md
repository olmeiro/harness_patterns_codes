# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Rama `replanning/revisor-ci`, sin commitear: revisor de CI con Azure OpenAI (`.github/workflows/revisor.yml` + `scripts/revisor_ci.py`, `pull_request_target`), acciones a Node 24. Gate verde (29 tests). Revisor: `accept` en la vuelta 3 (revise en las vueltas 1 y 2, todo corregido). Secrets y variable (`gpt-5.2`) ya configurados en GitHub. Constitución sin llenar (`/specs init` pendiente).

## Siguiente paso

Commit y PR de `replanning/revisor-ci` a `main` (protegido solo por `gate`). Tras el merge, un PR de prueba para que `revisor` corra por primera vez contra Azure; luego añadir `revisor` como required check en el ruleset de `main`.

## Bloqueos

- `the_agent_loop/.env.template`: añadir `AZURE_OPENAI_EVALUATOR_*` a mano (el deny `**/.env.*` de `settings.json` también bloquea el template).

## Registro de sesiones

2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — accept en la vuelta 3, listo para PR.
