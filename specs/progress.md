# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Revisor de CI en `main` (PR #1): `.github/workflows/revisor.yml` + `scripts/revisor_ci.py` con `gpt-5.2`. Gate verde en CI (29 tests), ya sin el aviso de Node 20. `revisor` aún no es required check porque no ha corrido nunca. Constitución sin llenar (`/specs init` pendiente).

## Siguiente paso

Comprobar que `revisor` corre en el PR `chore/progreso-tras-revisor-ci` y, si da su veredicto, añadirlo como required check en el ruleset de `main`.

## Bloqueos

- El deny `**/.env.*` de `.claude/settings.json` también bloquea `.env.template`, que AGENTS.md pide mantener: decidir si se exceptúa.

## Registro de sesiones

2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — mergeado en PR #1; falta probar `revisor` en un PR.
