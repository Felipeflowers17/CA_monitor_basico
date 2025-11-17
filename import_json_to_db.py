# -*- coding: utf-8 -*-
"""
Script de Importación Masiva (One-Time Use).

Este script carga un archivo JSON de scraping (Fase 1)
y lo inserta en la base de datos, siguiendo el flujo ELT.

EJECUCIÓN:
1. Coloca tu archivo JSON en la carpeta /data/
2. Actualiza la variable JSON_FILE_NAME (línea 24).
3. Ejecuta en la terminal: poetry run python import_json_to_db.py
"""

import sys
import json
from pathlib import Path

# --- Configuración del Path (igual que en run_app.py) ---
FILE = Path(__file__).resolve()
ROOT = FILE.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
# ------------------------------

# Importar los servicios que necesitamos
from src.db.session import SessionLocal
from src.db.db_service import DbService
from src.logic.score_engine import ScoreEngine
from src.utils.logger import configurar_logger

logger = configurar_logger("import_json_script")

# --- ¡CONFIGURA ESTO! ---
JSON_FILE_NAME = "compras_agiles_masivas_20251023_195931.json"  # <-- CAMBIA ESTO por el nombre de tu archivo
# ---------------------------

JSON_FILE_PATH = ROOT / "data" / JSON_FILE_NAME


def load_json_file() -> list:
    """Carga el archivo JSON desde la carpeta /data/"""
    logger.info(f"Cargando archivo JSON: {JSON_FILE_PATH}")
    try:
        # Forzamos la codificación utf-8 por si acaso
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            datos = json.load(f)

        if not isinstance(datos, list):
            logger.error(f"Error: El JSON en '{JSON_FILE_NAME}' no es una lista.")
            return []

        logger.info(f"Se cargaron {len(datos)} registros del JSON.")
        return datos
    except FileNotFoundError:
        logger.critical(f"Error Fatal: No se encontró el archivo en {JSON_FILE_PATH}")
        return []
    except json.JSONDecodeError:
        logger.critical(f"Error Fatal: El archivo '{JSON_FILE_NAME}' no es un JSON válido.")
        return []
    except Exception as e:
        logger.critical(f"Error inesperado al leer el JSON: {e}", exc_info=True)
        return []


def run_transform_phase(db_service: DbService, score_engine: ScoreEngine):
    """
    Paso (T)ransform: Ejecuta el cálculo de puntajes.
    Copia la lógica de 'EtlService._transform_puntajes_fase_1'
    """
    logger.info("Iniciando (Transform) Fase 1: Cálculo de puntajes...")
    try:
        # 1. Obtener CAs nuevas (score=0)
        licitaciones_a_puntuar = (
            db_service.obtener_candidatas_para_recalculo_fase_1()
        )

        if not licitaciones_a_puntuar:
            logger.info("No hay CAs nuevas para puntuar (ya estaban puntuadas).")
            return

        logger.info(f"Se puntuarán {len(licitaciones_a_puntuar)} CAs...")

        lista_para_actualizar = []
        for licitacion in licitaciones_a_puntuar:
            # 2. Crear el dict crudo que espera el ScoreEngine
            item_raw = {
                'nombre': licitacion.nombre,
                'estado_ca_texto': licitacion.estado_ca_texto,
                'organismo_comprador': licitacion.organismo.nombre if licitacion.organismo else ""
            }

            # 3. Calcular puntaje
            puntaje = score_engine.calcular_puntuacion_fase_1(item_raw)
            lista_para_actualizar.append((licitacion.ca_id, puntaje))

        # 4. Guardar puntajes en la BD
        db_service.actualizar_puntajes_fase_1_en_lote(lista_para_actualizar)
        logger.info("Transformación (T) Fase 1 completada.")

    except Exception as e:
        logger.error(f"Error en (Transform) Fase 1: {e}", exc_info=True)
        raise e


def main():
    """Función principal del script de importación."""
    logger.info("--- Iniciando Script de Importación de JSON (ELT) ---")

    # 1. Cargar datos del archivo
    datos_json = load_json_file()
    if not datos_json:
        logger.error("Proceso detenido. No se cargaron datos.")
        return

    # 2. Inicializar Servicios (La 'Raíz' de DI)
    logger.info("Inicializando servicios (DbService, ScoreEngine)...")
    db_service = DbService(SessionLocal)
    score_engine = ScoreEngine(db_service)
    logger.info("Servicios inicializados.")

    # 3. (L)oad - Cargar datos crudos en la BD
    logger.info("--- FASE (L)OAD ---")
    try:
        db_service.insertar_o_actualizar_licitaciones_raw(datos_json)
    except Exception as e:
        logger.critical(f"Error fatal durante la fase de Carga (Load): {e}", exc_info=True)
        return

    # 4. (T)ransform - Calcular puntajes
    logger.info("--- FASE (T)RANSFORM ---")
    try:
        run_transform_phase(db_service, score_engine)
    except Exception as e:
        logger.critical(f"Error fatal durante la fase de Transformación (Transform): {e}", exc_info=True)
        return

    logger.info("--- ¡Importación de JSON completada exitosamente! ---")
    logger.info(f"Se han cargado y puntuado {len(datos_json)} CAs.")
    logger.info("Puedes verificar los datos en tu BD o ejecutando la aplicación.")


if __name__ == "__main__":
    main()