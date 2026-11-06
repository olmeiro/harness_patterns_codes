import os
from copy import deepcopy
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. Configurar Azure OpenAI
client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # el .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
)

MODEL = os.environ["AZURE_OPENAI_DEPLOYMENT"]


# 2. Sesión con patrón Memento
class Session:
    def __init__(self, file_path):
        self.file = Path(file_path)
        self.messages = []
        self.checkpoints = {}
        self.turn = 0

    def checkpoint(self, turn):
        """Guardar mensajes y archivo antes del cambio."""
        self.checkpoints[turn] = {
            "messages": deepcopy(self.messages),
            "file_content": self.file.read_text(
                encoding="utf-8"
            ),
        }

    def edit(self, instruction):
        """Solicitar a Azure OpenAI una modificación."""
        turn = self.turn + 1

        # Memento: guardar estado antes de modificar
        self.checkpoint(turn)

        current_content = self.file.read_text(
            encoding="utf-8"
        )

        user_message = {
            "role": "user",
            "content": (
                f"Documento actual:\n{current_content}\n\n"
                f"Modificación solicitada:\n{instruction}"
            ),
        }

        # Responses API
        response = client.responses.create(
            model=MODEL,
            instructions=(
                "Eres un editor de documentos Markdown. "
                "Devuelve únicamente el contenido completo "
                "del documento actualizado, sin bloques "
                "de código ni explicaciones."
            ),
            input=self.messages + [user_message],
        )

        new_content = response.output_text

        if not new_content.strip():
            raise ValueError("El modelo no devolvió contenido")

        # Aplicar modificación al archivo
        self.file.write_text(
            new_content,
            encoding="utf-8"
        )

        # Actualizar conversación
        self.messages.extend([
            user_message,
            {"role": "assistant", "content": new_content},
        ])

        self.turn = turn
        print(f"Turno {turn}: documento actualizado")

    def rewind(self, turn):
        """Restaurar un checkpoint anterior."""
        snapshot = self.checkpoints[turn]

        # Restaurar conversación
        self.messages = deepcopy(snapshot["messages"])

        # Restaurar archivo
        self.file.write_text(
            snapshot["file_content"],
            encoding="utf-8"
        )

        # Continuar desde el estado restaurado
        self.turn = turn - 1
        self.checkpoints = {
            t: cp for t, cp in self.checkpoints.items()
            if t < turn
        }

        print(f"Restaurado al estado anterior al turno {turn}")


# 3. Ejemplo de ejecución
Path("plan.md").write_text(
    "# Plan del proyecto\n",
    encoding="utf-8"
)

session = Session("plan.md")

# Turno 1
session.edit(
    "Agrega una sección de objetivos del proyecto."
)

# Turno 2
session.edit(
    "Reemplaza el documento por una propuesta diferente."
)

# Recuperar estado anterior al turno 2
session.rewind(2)

print(Path("plan.md").read_text(encoding="utf-8"))