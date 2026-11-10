# Tech-stack — <nombre del proyecto>

> Constitución. Define el **marco técnico común**. Cualquier desviación se registra en [[decisions]] o en `replanning/`.

<!-- IA: greenfield → pregunta a la persona; propone opciones solo si te lo pide.
     Brownfield → extrae de los manifiestos de dependencias, Dockerfile, pipelines e infraestructura como código, y cita la fuente.
     Lo que no sepas: "PENDIENTE: <pregunta>". Borra las secciones que no apliquen. -->

---

## 1. Lenguaje y framework

- **Lenguaje y versión**:
- **Framework y versión mínima**:
- **Gestor de dependencias**:

## 2. Convenciones de código

<!-- IA: tipado, idioma de docstrings y mensajes, logging, manejo de errores.
     Lo que ya verifica el gate no se repite aquí: se referencia su configuración. -->

## 3. Estructura de módulos

<!-- IA: árbol de carpetas principal y la responsabilidad de cada una. Brownfield: la estructura real, no la ideal. -->

## 4. Interfaces expuestas

<!-- IA: endpoints HTTP, colas, eventos o comandos que expone, y dónde está su contrato (OpenAPI, esquema). -->

## 5. Dependencias

### Base

<!-- IA: las que existen desde el inicio y para qué sirve cada una. -->

### Añadidas por features

<!-- IA: dependencia → feature que la introdujo. -->

## 6. Servicios externos

| Servicio | Uso | Autenticación |
|---|---|---|
| <!-- IA: nube, bases de datos, APIs de terceros, modelos de IA --> | | |

## 7. Entornos

| Entorno | Recursos | Notas |
|---|---|---|
| <!-- IA: dev, qa, prod; nombres de recursos, nunca secretos --> | | |

## 8. Configuración y secretos

<!-- IA: variables de entorno (nombre y propósito, nunca valores) y dónde viven los secretos (key vault, .env local fuera de git). -->

## 9. Seguridad

<!-- IA: autenticación, autorización, validación de entrada y manejo de datos sensibles. -->

## 10. Observabilidad

<!-- IA: logs estructurados, trazas y métricas, y dónde se consultan. -->

## 11. Testing

- **Unitarias**:
- **Integración o contrato**:
- **Humo en el entorno desplegado**:
- **Evidencia aceptada para cerrar una feature**: <!-- IA: ej.: "las pruebas solo en local no bastan; hace falta humo en qa". -->

## 12. CI/CD y despliegue

<!-- IA: plataforma de pipelines, qué ejecuta (como mínimo el gate: python scripts/gate.py), cómo se despliega y quién aprueba. -->

## Relación con otros documentos

- [[mission]] — el porqué que justifica este stack.
- [[alcance-inicial]] — dependencias externas y punto de partida.
- [[roadmap]] — en qué orden entran estos componentes.
- [[decisions]] — decisiones técnicas que complementan este documento.
