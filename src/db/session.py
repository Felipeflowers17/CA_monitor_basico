# -*- coding: utf-8 -*-
"""
Configuración de la Sesión de Base de Datos (SQLAlchemy).

"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Importa la URL de la BD desde el archivo de configuración central
from config.config import DATABASE_URL
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

# --- Creación del Engine ---
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verifica la conexión antes de usarla
        echo=False,
        
        # Le decimos al driver (psycopg2) que use UTF-8
        # para comunicarse con el servidor de PostgreSQL.
        client_encoding='utf8'
    )
    logger.info("Engine de SQLAlchemy creado exitosamente.")
except Exception as e:
    logger.critical(f"Error al crear el engine de SQLAlchemy: {e}")
    raise e

# --- Fábrica de Sesiones (SessionLocal) ---
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)

logger.info("Fábrica de sesiones (SessionLocal) configurada.")

# --- Función de Dependencia (para la futura API) ---
def get_db_session():
    """
    Función de dependencia para obtener una sesión de BD.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()