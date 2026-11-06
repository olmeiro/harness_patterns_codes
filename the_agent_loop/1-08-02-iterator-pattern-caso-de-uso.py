#Imagina que tenemos un agente de IA que debe revisar 10.000 correos electrónicos buscando mensajes urgentes. No queremos descargar los 10.000 correos, sino solicitarlos progresivamente y detenernos cuando encontremos lo que necesitamos.


# ========================================
# 1. SIMULAMOS UN SERVIDOR DE CORREOS
# ========================================

BUZON = [
    {"id": 1, "asunto": "Factura de octubre"},
    {"id": 2, "asunto": "Boletín semanal"},
    {"id": 3, "asunto": "Recordatorio de reunión"},
    {"id": 4, "asunto": "URGENTE: servidor caído"},
    {"id": 5, "asunto": "Promoción de viajes"},
    {"id": 6, "asunto": "Reporte de ventas"},
]


def obtener_pagina(cursor, limite=2):
    """Simula una API que devuelve correos paginados."""
    print(f"📥 Consultando página desde posición {cursor}")

    correos = BUZON[cursor:cursor + limite]

    siguiente = cursor + limite
    if siguiente >= len(BUZON):
        siguiente = None

    return correos, siguiente


# ========================================
# 2. NUESTRO PATRÓN ITERATOR
# ========================================

class EmailIterator:

    def __init__(self):
        self.cursor = 0
        self.buffer = []
        self.terminado = False

    def __iter__(self):
        return self

    def __next__(self):

        # Solo consulta la API cuando se
        # han consumido los correos disponibles
        if not self.buffer:

            if self.terminado:
                raise StopIteration

            self.buffer, siguiente = obtener_pagina(
                self.cursor
            )

            if siguiente is None:
                self.terminado = True
            else:
                self.cursor = siguiente

            if not self.buffer:
                raise StopIteration

        # Entrega UN correo a la vez
        return self.buffer.pop(0)


# ========================================
# 3. CONSUMIDOR: BUSCAR CORREOS URGENTES
# ========================================

for correo in EmailIterator():

    print(f"🔍 Revisando: {correo['asunto']}")

    if "URGENTE" in correo["asunto"].upper():
        print(f"🚨 Encontrado: {correo['asunto']}")
        break
