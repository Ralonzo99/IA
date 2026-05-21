import streamlit as st
from docling.document_converter import DocumentConverter

@st.cache_resource
def get_converter():
    return DocumentConverter()

def extraer_texto(ruta_archivo):

    converter = get_converter()

    resultado = converter.convert(ruta_archivo)

    return resultado.document.export_to_markdown()
