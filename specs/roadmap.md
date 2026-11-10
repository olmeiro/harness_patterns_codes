# Roadmap — <nombre del proyecto>

> Constitución. Secuencia de features pequeñas, implementables y verificables, con su estado.

<!-- IA: deriva las features de [[mission]] y [[alcance-inicial]]. Cada feature cabe en una rama y cada documento de su spec en 250 líneas como máximo; si no, pártela.
     Brownfield: la primera fase suele ser asegurar la base (tests de lo existente, gate en verde) antes de cambiar comportamiento. -->

---

## 1. Principios de secuenciación

1. **Base antes que features**: configuración, contratos y el gate en verde van primero.
2. **La primera feature es manejable, no la más riesgosa**: sirve para probar el flujo y la arquitectura.
3. **Cada feature deja el sistema funcionando** y es verificable por sí sola.
4. **Replanning entre fases**: se revisa si el plan sigue siendo válido.

<!-- IA: añade los principios propios del proyecto, si los hay. -->

## 2. Fases

### Fase 0 — Constitución

`mission`, `tech-stack`, `alcance-inicial` y este roadmap. **Salida**: base documental versionada.

### Fase 1 — <nombre>

<!-- IA: objetivo de la fase y su criterio de salida. Repite el bloque por cada fase. -->

## 3. Features

| ID | Nombre | Fase | Depende de | Estado | Carpeta |
|---|---|---|---|---|---|
| 01 | <!-- IA --> | 1 | — | not_started | `features/01-<nombre>/` |

Estados: `not_started → in_progress → passing → accepted` (ver [[orden_spec]] §6). Una feature solo pasa a `accepted` con el veredicto `accept` del revisor.

## 4. Cierre del roadmap

<!-- IA: condición que da por cumplido el roadmap. Ej.: todas las features en accepted y los objetivos medibles de mission alcanzados. -->
