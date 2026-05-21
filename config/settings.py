from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
DATABASE_NAME = os.getenv("DATABASE_NAME", "sistema_gastos.db")
EXPORT_PATH = os.getenv("EXPORT_PATH", "exports/Gastos.xlsx")
