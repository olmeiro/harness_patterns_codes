# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Revisor de CI en `main` y obligatorio (ruleset con `gate` y `revisor`). PR #3 (`chore/ask-git-commit`): commits, push y `gh pr merge` piden confirmación (reglas `ask` + `validar_comando.py`), comprobado en modo auto; en revisión en CI. Plantilla `harness-python` preparada en local con los mismos cambios, sin publicar. Constitución sin llenar.

## Siguiente paso

PR de `chore/ask-git-commit`; publicar `harness-python` y marcarlo como Template repository; luego `/specs init` en `init/constitucion`.

## Bloqueos

Ninguno.

## Registro de sesiones

2026-11-11 — confirmación obligatoria para commits/push y plantilla `harness-python` — accept del revisor; pendientes PR y publicación.
2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — mergeado (PR #1) y probado en CI (PR #2).
