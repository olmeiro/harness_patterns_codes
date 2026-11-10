@../AGENTS.md

## Claude Code

- El hook `Stop` ejecuta el gate si editaste archivos desde el último gate verde, y no te deja terminar mientras falle.
- La revisión independiente la hace el subagente `revisor` (`@agent-revisor`): obtiene el diff él mismo, ejecuta el gate y termina con `VEREDICTO: accept | revise | block`.
- La skill `/specs` llena las specs: `init` (Constitución), `feature NN-nombre` (spec antes de programar) y `cerrar NN-nombre` (gate, revisor y estado).
- `validar_comando.py` bloquea comandos destructivos y cualquier acceso a `.env` (salvo `.env.template`). `post_edit.py` formatea y revisa cada archivo que editas.
