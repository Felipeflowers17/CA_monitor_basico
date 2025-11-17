# -*- coding: utf-8 -*-
"""
Punto de Entrada Principal de la Aplicación.
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
        # Rutas para el ejecutable congelado
        if getattr(sys, 'frozen', False):
            # En el .exe, alembic.ini está en la raíz temporal (_MEI...)
            # Y la carpeta alembic también.
            base_path = Path(sys._MEIPASS) # Ruta temporal de PyInstaller
            alembic_cfg_path = base_path / "alembic.ini"
            script_location = base_path / "alembic"
        else:
            # En modo script
            alembic_cfg_path = BASE_DIR / "alembic.ini"
            script_location = BASE_DIR / "alembic"

        if not alembic_cfg_path.exists():
            logger.error(f"No se encontró alembic.ini en: {alembic_cfg_path}")
            return

        logger.info(f"Ejecutando migraciones usando config: {alembic_cfg_path}")
        
        alembic_cfg = Config(str(alembic_cfg_path))
        alembic_cfg.set_main_option("script_location", str(script_location))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # Ejecutar upgrade head
        upgrade(alembic_cfg, "head")
        logger.info("¡Migraciones completadas con éxito!")

    except Exception as e:
        logger.critical(f"Error al ejecutar migraciones: {e}", exc_info=True)

def main():
    logger.info("=====================================")
    logger.info("Iniciando Monitor de Compras Ágiles...")
    logger.info("=====================================")

    # 1. Ejecutar Migraciones (Bloqueante) para asegurar que la BD esté actualizada
    run_migrations()

    # 2. Iniciar GUI
    try:
        from src.gui.gui_main import run_gui
        run_gui()
    except Exception as e:
        logger.critical(f"Error fatal en main: {e}", exc_info=True)
        input("Presione ENTER para salir...")

if __name__ == "__main__":
    main()