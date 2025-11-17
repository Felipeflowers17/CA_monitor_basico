# -*- coding: utf-8 -*-
"""
Configuración centralizada del Logger.

Proporciona una función 'configurar_logger' que puede ser llamada
por cualquier módulo para obtener un logger con un nombre específico,
asegurando que todos los logs sigan el mismo formato y vayan
a los mismos destinos (consola y archivo).
"""

import logging
import sys
from pathlib import Path

# Define el directorio de logs dentro de /data/
# (../.. para salir de src/utils y llegar a la raíz)
LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"

# Crea el directorio si no existe
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Define el formato de los logs
FORMATO_LOG = "%(asctime)s - %(levelname)-8s - %(name)-15s - %(message)s"

# Configura el logging básico (solo a archivo)
logging.basicConfig(
    level=logging.DEBUG,
    format=FORMATO_LOG,
    filename=LOG_DIR / "app.log",  # Archivo de log principal
    filemode="a",  # 'a' para añadir (append), 'w' para sobrescribir
    encoding="utf-8",
)

# --- Configuración del Handler de Consola ---


# 1. Crear el handler de consola
consola_handler = logging.StreamHandler(sys.stdout)
consola_handler.setLevel(logging.INFO)  # Muestra INFO o superior en consola

# 2. Crear el formateador y asignarlo al handler
formateador = logging.Formatter(FORMATO_LOG)
consola_handler.setFormatter(formateador)

# 3. Añadir el handler al logger raíz
root_logger = logging.getLogger()
if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
    root_logger.addHandler(consola_handler)


def configurar_logger(nombre_modulo: str) -> logging.Logger:
    """
    Obtiene una instancia de logger para un módulo específico.

    """
    return logging.getLogger(nombre_modulo)


# --- Prueba rápida (se ejecuta solo si corres este archivo directamente) ---
if __name__ == "__main__":
    logger = configurar_logger("prueba_logger")
    logger.debug("Este es un mensaje DEBUG (solo en archivo)")
    logger.info("Este es un mensaje INFO (archivo y consola)")
    logger.warning("Este es un mensaje WARNING")
    logger.error("Este es un mensaje ERROR")
    logger.critical("Este es un mensaje CRITICAL")
