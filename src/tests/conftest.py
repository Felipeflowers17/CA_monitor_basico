# -*- coding: utf-8 -*-
"""
Configuración global de Pytest (conftest.py).

Aquí definimos los "fixtures": recursos compartidos que las pruebas
pueden solicitar (como una conexión a base de datos limpia).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importamos tus modelos y la base
from src.db.db_models import Base, CaLicitacion, CaSeguimiento, CaOrganismo, CaSector
from src.db.db_service import DbService

# Usamos SQLite en memoria para pruebas rápidas y aisladas.
# check_same_thread=False es necesario porque SQLite a veces se queja con hilos.
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """Crea el motor de base de datos (Engine) una sola vez por sesión de pruebas."""
    engine = create_engine(
        TEST_DATABASE_URL, 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    return engine

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Crea una sesión de base de datos nueva para CADA función de prueba.
    Crea las tablas antes del test y las borra después.
    """
    # 1. Crear las tablas en la BD en memoria
    Base.metadata.create_all(engine)
    
    # 2. Crear la sesión
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    yield session  # Aquí es donde corre el test
    
    # 3. Limpieza: Cerrar sesión y borrar tablas
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_service(db_session):
    """
    Entrega una instancia de tu DbService conectada a la BD de pruebas.
    Simulamos el session_factory usando una lambda que devuelve la sesión actual.
    """
    # DbService espera un session_factory (algo llamable que devuelva una sesión)
    # Creamos un fake_factory
    fake_factory = lambda: db_session
    service = DbService(fake_factory)
    return service