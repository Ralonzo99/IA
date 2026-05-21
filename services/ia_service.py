import json
import ollama

from config.settings import OLLAMA_MODEL
from schemas.factura_schema import FacturaEstructurada

PROMPT_SISTEMA = '''
Eres un asistente experto en análisis de facturas.
Debes devolver SOLO JSON válido.
'''

def analizar_factura(texto):

    respuesta = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "system",
                "content": PROMPT_SISTEMA
            },
            {
                "role": "user",
                "content": texto
            }
        ]
    )

    contenido = respuesta["message"]["content"].strip()

    try:

        if contenido.startswith("```"):
            contenido = contenido.replace("```json", "")
            contenido = contenido.replace("```", "")

        datos = json.loads(contenido)

        return FacturaEstructurada(**datos)

    except Exception:
        return None
