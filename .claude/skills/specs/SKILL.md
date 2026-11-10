---
name: specs
description: Llena las specs SDD de specs/ a partir de sus plantillas. Úsala para crear la Constitución de un proyecto nuevo o legacy, la spec de una feature antes de programarla o el cierre de una feature (gate, revisor, roadmap, changelog, progress). No implementa ni corrige código.
argument-hint: "init | feature <NN-nombre> | cerrar <NN-nombre>"
---

# Specs

Modo: `$0`. Feature: `$1`.

Sin modo o con uno desconocido, muestra los tres modos de abajo y pregunta cuál. Si no existe `specs/orden_spec.md`, para: pide a la persona que copie la carpeta `specs/` del harness.

## Reglas comunes

- **Lee primero `specs/orden_spec.md` §2** y aplica sus reglas:
  - En greenfield preguntas.
  - En brownfield infieres, citas `archivo:línea` y marcas `[inferido]`.
  - Lo que no sepas lo escribes como `PENDIENTE: <pregunta>`; nunca lo inventas.
  - Borras las secciones que no apliquen.
  - En los documentos que llenes en este modo no queda ningún comentario `<!-- IA -->`, y ninguno pasa de 250 líneas.
- **Rama** (§7.1 y §10). Comprueba con `git status` que estás en `init/constitucion` (modo init) o en `feature/$1` (modos feature y cerrar), sin cambios ajenos a la tarea. Si no, para y pide a la persona que la cree; no la crees tú.
- **No hagas commit ni push.** Al terminar:
  - propón el mensaje de commit (§11);
  - lista los `PENDIENTE:` que quedaron;
  - actualiza `specs/progress.md` con el estado, el siguiente paso y una línea en el registro.

## init: Constitución

1. **Postura.** Greenfield si casi no hay código; brownfield si lo hay. Si dudas, pregunta. Escríbela en `orden_spec.md`.
2. **Brownfield: explora antes de escribir.** Mira README, manifiestos de dependencias, estructura de carpetas, tests, pipelines y configuración. Sin abrir `.env` ni secretos.
3. **Llena en orden** `mission.md` → `tech-stack.md` → `alcance-inicial.md` → `roadmap.md`. Cada uno se apoya en los anteriores.
4. **Greenfield: pregunta por documento.** Agrupa las preguntas de cada documento en una sola ronda en lugar de hacerlas una a una.
5. **Roadmap.** La primera feature es manejable, no la más riesgosa. Todas empiezan en `not_started`.

## feature: spec de `$1`

1. **Roadmap.** Comprueba que la feature está en `roadmap.md`, que es la siguiente según su orden y que sus dependencias están `accepted`. Si algo no se cumple, para y pregunta: cambiar el roadmap es replanning.
2. **Carpeta.** Copia `specs/features/_plantilla/` a `specs/features/$1/`. Si ya existe, no la sobrescribas: completa lo que falte.
3. **Llena en orden** `brief.md` → `plan.md` → `requirements.md` → `validation.md`. Deja `review.md` como está.
   - Brownfield: lee el código afectado antes de escribir `plan.md` y describe el comportamiento actual en `requirements.md`.
   - Cada `CA-N` de `requirements.md` tiene su fila en `validation.md`.
4. **Coherencia.** Lo que incluye el brief está cubierto por los `CA-N`, cada `CA-N` tiene su verificación y "No tocar" no contradice el plan. Corrige lo que no cuadre.
5. **Pendientes.** Pregunta los `PENDIENTE:` que queden e incorpora las respuestas.
6. **Estado.**
   - Si en brief, plan, requirements y validation no queda ningún `PENDIENTE:` ni comentario `<!-- IA -->`, pasa la feature a `in_progress` en `roadmap.md`. Ese cambio va en el commit de la spec que propones.
   - Si quedan, déjala en `not_started` y dilo.

## cerrar: cierre de `$1`

1. **Gate.** Ejecuta `python scripts/gate.py`. Si falla, para: la feature no está `passing`. Si pasa, márcala `passing` en `roadmap.md`.
2. **Evidencia.** En `review.md`, llena Gate, Cumplimiento por criterio, Errores encontrados al validar y Desviaciones de la spec.
   - La evidencia de cada `CA-N` es real (comando y salida), según `validation.md`.
   - La evidencia de las pruebas manuales se la pides a la persona.
   - En "Errores encontrados al validar", añade filas; no borres las de vueltas anteriores.
3. **Revisión independiente.** Lanza el subagente `revisor` pasándole solo `specs/features/$1/`, sin tu resumen ni tu valoración.
4. **Veredicto.** Cópialo a `review.md` junto con el número de vuelta, y actúa según `orden_spec.md` §7.4:
   - `accept`:
     - márcala `accepted` en `roadmap.md`;
     - actualiza `CHANGELOG.md` si la entrega es relevante (§12);
     - llena "Deuda técnica y temas para replanning";
     - si algo cambia la Constitución o el roadmap, propón abrir un replanning.
   - `revise`:
     - anota en "Errores encontrados al validar" lo que pide el revisor y su destino (§8), y para;
     - el código se corrige fuera de esta skill, y después se vuelve a ejecutar `/specs cerrar $1`;
     - si es el tercer `revise`, trátalo como `block`.
   - `block`: para y pregunta a la persona.
