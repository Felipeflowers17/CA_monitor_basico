"""
Módulo de Base de Datos.

Exporta los componentes clave para que sean fácilmente importables
desde otros servicios.
"""

# Exporta la 'Base' para que Alembic la vea
from .db_models import Base, CaLicitacion, CaSeguimiento  # noqa: F401

# Exporta la 'clase de servicio'
from .db_service import DbService  # noqa: F401

# Exporta la 'fábrica de sesiones'
from .session import SessionLocal, engine  # noqa: F401
