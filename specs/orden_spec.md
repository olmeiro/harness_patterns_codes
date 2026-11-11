# Orden de trabajo SDD

> Cómo se trabaja este repositorio con Spec-Driven Development: qué archivo se usa en cada momento, cómo se relacionan specs, código y harness, y cuándo una feature está terminada.

**Postura del proyecto**: <!-- IA: greenfield (repo nuevo) o brownfield (código existente). Pregúntalo si no es obvio. --> PENDIENTE

---

## 1. Principios

1. **Spec antes que código.** Ninguna feature se implementa sin su carpeta en `features/`.
2. **El repo guarda código e intención.** Las specs se versionan, se revisan en el PR y se corrigen cuando cambia la intención.
3. **Una feature = una rama = una unidad revisable.**
4. **Commits pequeños, en español.**
5. **Sin drift.** Si el código cambia la intención, la spec se actualiza en el mismo cambio.
6. **Quien implementa no decide si está terminado.** Lo decide un revisor independiente contra la spec.
7. **Replanning entre features.** No se salta a la siguiente sin revisar el roadmap.

## 2. Cómo llena la IA estas plantillas

Cada plantilla trae comentarios `<!-- IA: ... -->` que dicen qué escribir y de dónde sacarlo. En Claude Code, la skill `/specs` aplica este método: `init`, `feature NN-nombre` y `cerrar NN-nombre`.

- **Greenfield**: pregunta a la persona lo que no esté en los documentos anteriores. No propongas alcance que nadie pidió.
- **Brownfield**: infiere del código, la configuración, los tests y la documentación existente, y cita la fuente (`archivo:línea`). Marca lo inferido con `[inferido]` hasta que la persona lo confirme.
- **Lo que no sepas** se escribe `PENDIENTE: <pregunta concreta>`. Nunca inventes nombres, cifras, servicios ni requisitos.
- Un documento terminado no conserva ningún comentario `<!-- IA -->`, tampoco el de cabecera. Las secciones que no apliquen se borran enteras. Mientras queden comentarios o `PENDIENTE:`, el documento no está terminado.
- Máximo 250 líneas por documento. Si crece más, el alcance es demasiado grande: pártelo.

## 3. Estructura

```text
specs/
├─ orden_spec.md          # este documento: el método
├─ mission.md             # por qué existe el proyecto              ┐
├─ tech-stack.md          # con qué se construye y opera             │ Constitución:
├─ alcance-inicial.md     # qué entra, qué no y el punto de partida  │ una vez por proyecto
├─ roadmap.md             # features en orden y su estado            ┘
├─ decisions.md           # decisiones técnicas durables (DEC-NNN)
├─ progress.md            # estado actual y siguiente paso
├─ CHANGELOG.md           # entregas relevantes
├─ features/
│  ├─ _plantilla/         # se copia, no se llena
│  └─ NN-nombre/          # brief · plan · requirements · validation · review
└─ replanning/
   ├─ _plantilla.md
   └─ AAAA-MM-DD-tema.md
```

Si varias features comparten un catálogo del dominio (estados, tipos, códigos), créalo como `specs/catalogo.md` para que ninguna lo redefina por su cuenta.

## 4. Constitución

Se llena en este orden: `mission` → `tech-stack` → `alcance-inicial` → `roadmap`. Basta con que sea suficientemente clara para empezar; se refina en cada replanning.

| Archivo | Responde |
|---|---|
| `mission.md` | Por qué existe, para quién, qué restricciones tiene y cómo se mide el éxito. |
| `tech-stack.md` | Lenguaje, framework, servicios, entornos, seguridad, observabilidad, testing y despliegue. |
| `alcance-inicial.md` | Qué entra y qué no, dependencias externas y desde dónde arranca (activos heredados o código existente). |
| `roadmap.md` | Fases, features, dependencias y el estado de cada feature. |

## 5. Archivos de una feature

Se crean en este orden copiando `features/_plantilla/` a `features/NN-nombre/`.

| Archivo | Cuándo | Contiene | No contiene |
|---|---|---|---|
| `brief.md` | primero | problema, por qué ahora, qué incluye y qué no, resultado esperado | cómo se construye |
| `plan.md` | antes de programar | enfoque, archivos a tocar, secuencia, riesgos, qué no tocar | criterios funcionales |
| `requirements.md` | antes de programar | comportamiento, reglas, casos borde, criterios de aceptación `CA-N` | pasos de implementación |
| `validation.md` | antes de programar | cómo se verifica cada `CA-N` y qué evidencia se guarda | resultados |
| `review.md` | al cerrar | gate, evidencia por `CA-N`, errores encontrados, veredicto del revisor | — |

`requirements.md` es el contrato: el revisor valida el diff contra sus `CA-N` y contra `validation.md`.

## 6. Estados de una feature

Viven en la tabla de `roadmap.md`: `not_started → in_progress → passing → accepted`.

| Estado | Significa |
|---|---|
| `not_started` | Está en el roadmap, sin spec. |
| `in_progress` | La spec está commiteada y se está implementando. |
| `passing` | `python scripts/gate.py` pasa. Lo marca quien implementa. |
| `accepted` | El revisor respondió `accept` contra la spec. Solo así se marca. |

## 7. Flujo por feature

### 1. Preparación
- `main` limpio y la feature anterior cerrada o pausada explícitamente.
- Confirmar en `roadmap.md` que es la siguiente correcta.
- `git checkout -b feature/NN-nombre`.

### 2. Especificación
- Llenar `brief`, `plan`, `requirements` y `validation`, y revisar que sean coherentes entre sí.
- Commit de la spec **antes** de programar. Estado → `in_progress`.

### 3. Implementación
- Grupos pequeños; cada uno deja el gate en verde y es un commit.
- Si el código obliga a cambiar la intención, se actualiza la spec en el mismo commit.
- Gate en verde al terminar → `passing`.
- Completar en `review.md` la sección del gate y la evidencia por `CA-N`.

### 4. Validación independiente
El revisor empieza con contexto limpio y lee la spec, el diff de toda la rama (`git diff main...HEAD` más lo no commiteado) y la evidencia. No recibe el resumen de quien implementó.

```bash
# En la misma sesión (subagente con su propio contexto)
@agent-revisor valida specs/features/NN-nombre/
# En otra sesión
claude -p --agent revisor "Valida specs/features/NN-nombre/"
# En el PR: .github/workflows/revisor.yml (obliga a mergear solo si es required check en main)
```

| Veredicto | Siguiente paso |
|---|---|
| `accept` | Estado → `accepted`. Se puede commitear el cierre y abrir el PR. |
| `revise` | Vuelve a implementación con lo que falta. **Máximo 2 vueltas**; la tercera se trata como `block`. |
| `block` | Se para y se pregunta a la persona: falta una decisión o información. |

Cada vuelta queda en `review.md`: qué encontró, por qué pasó y qué se cambió.

### 5. Cierre
- Completar `review.md` con el veredicto.
- Actualizar `CHANGELOG.md` si la entrega es relevante y `progress.md`.
- PR y merge a `main`.
- Abrir un replanning si algo lo amerita.

## 8. Errores: de hallazgo a harness

Los errores que aparecen al validar se registran en el `review.md` de su feature, no en un archivo global. Cada uno termina en un destino:

| Si el error… | Se convierte en |
|---|---|
| es puntual | la corrección y un test que fallaría sin ella |
| se repite por segunda vez | una línea en `AGENTS.md` |
| se repite siempre en el mismo paso | una skill |
| puede costar datos, dinero o seguridad | un permiso, un hook o una regla del gate: el texto no siempre se cumple |

En cada replanning se revisan los `review.md` recientes para detectar repeticiones.

## 9. Continuidad entre sesiones

Cada sesión empieza sin contexto: lo que no esté en el repo no existe para la siguiente.

**Al empezar**: leer `progress.md`, ejecutar `git log --oneline -10` y ejecutar el gate antes de tocar nada, para saber si la base está sana.

**Al terminar**: actualizar `progress.md` con el estado verificado y el siguiente paso.

**No se guarda**:
- Lo ya terminado: lo registra git. `progress.md` conserva solo las últimas 10 sesiones.
- Un informe por tarea: la evidencia de una feature vive en su `review.md`.
- Reglas o preferencias de trabajo: van en `AGENTS.md`.

## 10. Ramas

| Tipo | Patrón | Uso |
|---|---|---|
| Constitución | `init/constitucion` | Primera versión de la Constitución. |
| Feature | `feature/NN-nombre` | Una feature y su spec. No se mezclan dos features. |
| Replanning | `replanning/tema` | Cambios que afectan a la Constitución o al roadmap. |
| Research | `research/tema` | Ideas no comprometidas. No entran al roadmap hasta decidirse. |

## 11. Commits

[Conventional Commits](https://www.conventionalcommits.org/) con el mensaje en español:

```text
docs(specs): define la spec de 03-autenticacion
feat(autenticacion): agrega el login con token
fix(autenticacion): alinea el error 401 con la spec
test(autenticacion): cubre el token expirado
docs(changelog): registra la entrega de 03-autenticacion
```

Momentos de commit: al cerrar la Constitución, al cerrar la spec (antes de programar), varios durante la implementación, tras la validación y tras el changelog.

## 12. Changelog

Resume entregas, no commits: git guarda el detalle. Se actualiza al cerrar una feature.

- **Sí entra**: feature nueva, fix importante, cambio de alcance o de comportamiento visible, integración nueva, decisión de arquitectura.
- **No entra**: commits intermedios, renombres, refactors sin impacto visible, pruebas exploratorias.

```markdown
## AAAA-MM-DD — NN-nombre
### Added
### Changed
### Fixed
### Notes
```

## 13. Drift entre spec y código

Si una revisión detecta que spec y código dicen cosas distintas, se clasifica antes de corregir:

- **Bug en el código** → se corrige el código.
- **Bug en la spec** → se corrige la spec.
- **Decisión nueva** descubierta al implementar → se actualiza la spec y, si aplica a más features, `decisions.md`.
- **Mejora futura** → va a replanning.

Spec y código corregidos van en el mismo commit.

## 14. Checklists

**Antes de empezar una feature**
- [ ] La Constitución existe y es mínimamente clara.
- [ ] El roadmap dice que esta es la siguiente.
- [ ] La rama está creada.
- [ ] `brief`, `plan`, `requirements` y `validation` están completos (sin `PENDIENTE:` ni comentarios `<!-- IA -->`) y commiteados.

**Antes de mergear**
- [ ] Gate en verde (`passing`).
- [ ] Veredicto `accept` del revisor (`accepted`).
- [ ] `review.md` completo y sin drift pendiente.
- [ ] `CHANGELOG.md` y `progress.md` actualizados si aplica.
- [ ] Lo que escala a replanning está anotado.
