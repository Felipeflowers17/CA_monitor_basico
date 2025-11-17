# -*- coding: utf-8 -*-
"""
Configuración General de la Aplicación.

"""

import os
import sys  
from dotenv import load_dotenv
from pathlib import Path

# --- INICIO DE LA LÓGICA PARA RUTAS DINÁMICAS ---
if getattr(sys, 'frozen', False):
    # Estamos ejecutando como un .exe (congelado)
    # La ruta base es la carpeta donde está el .exe
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Estamos ejecutando como un script normal (python run_app.py)
    # La ruta base es la raíz del proyecto (subiendo un nivel desde /config)
    BASE_DIR = Path(__file__).resolve().parent.parent
# ---

# Cargar variables de entorno desde el .env en la ruta base
env_path = BASE_DIR / ".env"
logger_path = BASE_DIR / "data" / "logs" / "app.log" # Para depuración
print(f"Buscando .env en: {env_path}") # Mensaje de depuración
print(f"Log se guardará en: {logger_path}")

load_dotenv(env_path, encoding="cp1252")


# --- Configuración de Base de Datos (PostgreSQL) ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Mensaje de error más específico
    raise ValueError(f"DATABASE_URL no está definida. Se buscó el archivo .env en: {env_path}")

# --- ¡UBICACIÓN DE CONSTANTES! ---
# Umbrales (movidos de score_config.py para romper importación circular)
UMBRAL_FASE_1 = 5  # Puntos mínimos para pasar a Fase 2
UMBRAL_FINAL_RELEVANTE = 9   # Puntos mínimos para ser "Relevante"

# --- Configuración de Scraping ---
URL_BASE_WEB = "https://buscador.mercadopublico.cl"
URL_BASE_API = "https://api.buscador.mercadopublico.cl"

TIMEOUT_REQUESTS = 40  # 40 segundos
DELAY_ENTRE_PAGINAS = 2 # 2 segundos
MODO_HEADLESS = os.getenv('HEADLESS', 'True').lower() == 'true'

HEADERS_API = {
    'X-Api-Key': 'e93089e4-437c-4723-b343-4fa20045e3bc'
}
PUNTOS_ORGANISMO = 0
PUNTOS_SEGUNDO_LLAMADO = 0
PUNTOS_KEYWORD_TITULO = 0
PUNTOS_ALERTA_URGENCIA = 0
PUNTOS_KEYWORD_PRODUCTO = 0