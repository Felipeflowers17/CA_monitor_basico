# -*- coding: utf-8 -*-
"""
Punto de Entrada Principal de la Aplicación (Producción).
"""

import sys
import os
from pathlib import Path

# --- Configuración del Path ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Importar logger y configuración
from src.utils.logger import configurar_logger
from config.config import DATABASE_URL

# Importaciones para Alembic
from alembic.config import Config
from alembic.command import upgrade

logger = configurar_logger("run_app")

def run_migrations():
    """Ejecuta las migraciones de Alembic antes de iniciar la GUI."""
    logger.info("Verificando estado de la base de datos...")
    try:
        # Rutas para el ejecutable congelado vs código fuente
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS) # Ruta temporal de PyInstaller
            alembic_cfg_path = base_path / "alembic.ini"
            script_location = base_path / "alembic"
        else:
            alembic_cfg_path = BASE_DIR / "alembic.ini"
            script_location = BASE_DIR / "alembic"

        if not alembic_cfg_path.exists():
            logger.error(f"No se encontró alembic.ini en: {alembic_cfg_path}")
            return

        logger.info(f"Ejecutando migraciones usando config: {alembic_cfg_path}")
        
        alembic_cfg = Config(str(alembic_cfg_path))
        alembic_cfg.set_main_option("script_location", str(script_location))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # Ejecutar upgrade head (silencioso si no hay cambios)
        upgrade(alembic_cfg, "head")
        logger.info("BD actualizada correctamente.")

    except Exception as e:
        # Si falla la migración, lo logueamos pero intentamos abrir la app igual
        # para no bloquear al usuario por errores menores de DB.
        logger.critical(f"Error al ejecutar migraciones: {e}", exc_info=True)

def main():
    # 1. Ejecutar Migraciones
    run_migrations()

    # 2. Iniciar GUI
    try:
        from src.gui.gui_main import run_gui
        run_gui()
    except Exception as e:
        logger.critical(f"Error fatal no manejado en la GUI: {e}", exc_info=True)
        # En producción, si falla fatalmente, mostramos el error rápido antes de salir
        print(f"Error Fatal: {e}")

if __name__ == "__main__":
    main()