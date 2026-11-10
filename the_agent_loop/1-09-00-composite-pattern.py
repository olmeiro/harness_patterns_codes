"""
Patrón Composite: una "carpeta" (CompositeBlock) y un "archivo" (TextBlock)
se tratan igual. Le pides algo a la raíz y ella se lo pide a sus hijos.

Cómo depurarlo en VS Code (F5 -> "Python File"):
  1. Pon breakpoints en las líneas marcadas con 🔴 BREAKPOINT.
  2. Al parar en ticket.redact() usa F11 (Step Into) para bajar por el árbol.
  3. En el panel CALL STACK verás la recursión: redact -> redact -> redact...
  4. En WATCH agrega: self.name, self.text, len(clean_children)
"""

import os
import re
from abc import ABC, abstractmethod  # ABC = "clase molde" que no se puede instanciar
from dataclasses import dataclass  # genera __init__ y __repr__ automáticamente

from dotenv import load_dotenv
from openai import OpenAI


# 1. Interfaz común (Component)
# Block es un CONTRATO: dice QUÉ métodos debe tener todo bloque, no CÓMO hacerlos.
# Al heredar de ABC, Block() da error: solo sirve como molde para las clases hijas.
class Block(ABC):
    # @abstractmethod = "toda clase hija ESTÁ OBLIGADA a implementar este método".
    # Si una hija no lo implementa, Python no deja crear objetos de ella.
    @abstractmethod
    def render(self) -> str:  # -> str es solo una pista de tipo: devuelve texto
        pass  # sin código: cada hija pone el suyo

    @abstractmethod
    def redact(self) -> "Block":
        pass

    @abstractmethod
    def count(self) -> int:
        pass


# 2. Elemento individual (Leaf)
# @dataclass escribe por ti el constructor. Equivale a:
#     def __init__(self, text): self.text = text
# Por eso puedes crear TextBlock("hola") sin haber escrito __init__.
@dataclass
class TextBlock(Block):  # (Block) = HERENCIA: TextBlock "es un" Block y cumple su contrato
    text: str  # atributo: el texto de la hoja

    # self = el objeto concreto que recibe la llamada (este TextBlock)
    def render(self) -> str:
        return self.text

    def redact(self) -> Block:
        # Ocultar correos electrónicos
        clean = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w+\b", "[EMAIL_OCULTO]", self.text)

        # Ocultar tokens y contraseñas simples
        clean = re.sub(r"(?i)\b(token|password|api_key)\s*[:=]\s*\S+", r"\1=[OCULTO]", clean)

        # 🔴 BREAKPOINT (hoja): aquí termina la bajada. Compara self.text vs clean
        return TextBlock(clean)

    def count(self) -> int:
        return 1


# 3. Contenedor (Composite)
# También es un Block, así que tiene los mismos métodos que TextBlock.
# @dataclass genera: def __init__(self, name, children): self.name = name; self.children = children
@dataclass
class CompositeBlock(Block):
    name: str  # título de la carpeta, ej. "Logs"
    children: list[Block]  # hijos: pueden ser TextBlock o CompositeBlock (ambos son Block)

    def render(self) -> str:
        lines = [f"[{self.name}]"]

        for child in self.children:
            for line in child.render().splitlines():
                lines.append("  " + line)

        return "\n".join(lines)

    def redact(self) -> Block:
        # El contenedor no limpia nada: delega en cada hijo, sea hoja o carpeta
        clean_children = []
        for child in self.children:
            # POLIMORFISMO: llamamos child.redact() sin saber si child es hoja o carpeta;
            # Python ejecuta el redact() de la clase real del objeto.
            # 🔴 BREAKPOINT (carpeta): mira self.name y type(child).__name__, luego F11
            clean_children.append(child.redact())

        return CompositeBlock(self.name, clean_children)

    def count(self) -> int:
        return sum(child.count() for child in self.children)


# 4. Construir ticket con elementos anidados
ticket = CompositeBlock(
    name="Ticket #1042",
    children=[
        CompositeBlock(
            name="Descripción",
            children=[
                TextBlock("La plataforma de pagos devuelve error 504. Contacto: ana@empresa.com")
            ],
        ),
        CompositeBlock(
            name="Comentarios",
            children=[
                TextBlock("Cliente: falla en 8 de 10 intentos."),
                TextBlock("Soporte: error reproducido."),
            ],
        ),
        CompositeBlock(
            name="Resultado de herramienta",
            children=[
                TextBlock("API /checkout: HTTP 504 Gateway Timeout."),
                CompositeBlock(
                    name="Logs",
                    children=[
                        TextBlock("Timeout en payments-api después de 30s."),
                        TextBlock("token=abc123456"),
                    ],
                ),
            ],
        ),
    ],
)


# 5. Aplicar Composite sobre todo el ticket
# 🔴 BREAKPOINT (inicio): una sola llamada a la raíz; F11 para entrar
clean_ticket = ticket.redact()

print("=== TICKET DEPURADO ===")
print(clean_ticket.render())

print("\nBloques de texto:", clean_ticket.count())


# 6. Configurar Azure OpenAI
load_dotenv()

client = OpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    # el .env ya incluye /openai/v1
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/",
)


# 7. Analizar el ticket con Responses API
response = client.responses.create(
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    instructions=(
        "Eres un analista de soporte técnico. "
        "Analiza el ticket y responde en español con: "
        "1. Resumen del problema. "
        "2. Prioridad: alta, media o baja. "
        "3. Posible causa. "
        "4. Acción recomendada. "
        "No inventes información."
    ),
    input=clean_ticket.render(),
    store=False,
)

print("\n=== ANÁLISIS DEL AGENTE ===")
print(response.output_text)

# ejecucion python 1-09-00-composite-pattern.py
