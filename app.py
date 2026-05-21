import streamlit as st

from database.repository import inicializar_db
from services.ocr_service import extraer_texto
from services.ia_service import analizar_factura
from services.storage_service import guardar_factura
from services.excel_service import exportar_excel
from utils.file_utils import guardar_archivo_temporal

st.set_page_config(
    page_title="OCR IA Facturas",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 Analizador Inteligente de Facturas")

inicializar_db()

archivo = st.file_uploader(
    "Sube una factura",
    type=["pdf", "png", "jpg", "jpeg"]
)

if archivo:

    if archivo.size > 10 * 1024 * 1024:
        st.error("El archivo supera los 10MB")
        st.stop()

    ruta_archivo = guardar_archivo_temporal(archivo)

    if st.button("Procesar factura"):

        with st.spinner("Extrayendo texto OCR..."):
            texto_extraido = extraer_texto(ruta_archivo)

        st.subheader("Texto Detectado")
        st.text_area(
            "OCR",
            texto_extraido,
            height=300
        )

        with st.spinner("Analizando con IA..."):
            factura = analizar_factura(texto_extraido)

        if factura:

            factura_id = guardar_factura(factura)

            exportar_excel()

            st.success(f"Factura guardada correctamente ID {factura_id}")

            st.subheader("Datos Detectados")
            st.json(factura.model_dump())

        else:
            st.error("No se pudo analizar la factura")
