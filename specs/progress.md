# Progreso

> Continuidad entre sesiones. Cada sesión empieza leyendo este archivo y lo actualiza al terminar.
> Lo terminado lo registra git: aquí solo vive el estado actual. El registro guarda las últimas 10 sesiones; borra las más antiguas.

## Estado actual

Revisor de CI en `main` y obligatorio (ruleset con `gate` y `revisor`). Rama `chore/ask-git-commit`: commits y push piden confirmación (reglas `ask` + `validar_comando.py`), comprobado en modo auto; revisor `accept` en la vuelta 3, gate verde (50 tests); falta commitear la última vuelta y abrir el PR. Plantilla `harness-python` armada en `C:\Users\OlmeiroOrozcoOrtiz\Downloads\harness-python` con los mismos cambios, sin commitear ni publicar. Constitución sin llenar.

## Siguiente paso

PR de `chore/ask-git-commit`; publicar `harness-python` y marcarlo como Template repository; luego `/specs init` en `init/constitucion`.

## Bloqueos

Ninguno.

## Registro de sesiones

2026-11-11 — confirmación obligatoria para commits/push y plantilla `harness-python` — accept del revisor; pendientes PR y publicación.
2026-11-11 — revisor independiente en CI con Azure OpenAI y acciones a Node 24 — mergeado (PR #1) y probado en CI (PR #2).
