@../AGENTS.md

## Claude Code

- El hook `Stop` ejecuta el gate si editaste archivos desde el último gate verde, y no te deja terminar mientras falle.
- La revisión independiente la hace el subagente `revisor` (`@agent-revisor`): obtiene el diff él mismo, ejecuta el gate y termina con `VEREDICTO: accept | revise | block`.
- La skill `/specs` llena las specs: `init` (Constitución), `feature NN-nombre` (spec antes de programar) y `cerrar NN-nombre` (gate, revisor y estado).
- Ningún `.env*` se puede leer ni editar, tampoco `.env.template`: lo impiden las reglas deny de `settings.json`.
- `validar_comando.py` bloquea comandos destructivos y el acceso a `.env` desde la terminal, y pide confirmación a la persona para los comandos que crean o publican commits (`git commit`, `push`, `merge`, `pull`, `am`…, y `gh pr merge`). No detecta alias de git y puede preguntar de más, p. ej. al buscar el texto `git commit` con `grep`. `post_edit.py` formatea y revisa cada archivo que editas.
