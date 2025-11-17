"""
Script de "Siembra" (Seeding) de la Base de Datos.

Este script puebla las tablas de configuración (CaKeyword,
CaOrganismoPrioritario) con los valores iniciales.

EJECUTAR SOLO UNA VEZ después de crear las tablas con Alembic.
"""

import sys
from pathlib import Path

# --- Configuración del Path (igual que en run_app.py) ---
FILE = Path(__file__).resolve()
ROOT = FILE.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
# ------------------------------

from src.db.session import SessionLocal
from src.db.db_models import CaKeyword, CaOrganismoPrioritario, CaOrganismo
from sqlalchemy import select

# --- ¡DEFINE AQUÍ TUS REGLAS INICIALES! ---

REGLAS_KEYWORDS = [
    # Tipo: 'titulo_pos', 'titulo_neg', 'producto'
    # (Keyword, Tipo, Puntos)
    ("computador", "titulo_pos", 5),
    ("notebook", "titulo_pos", 5),
    ("laptop", "titulo_pos", 5),
    ("impresora", "titulo_pos", 3),
    ("toner", "titulo_pos", 3),

    ("servicio", "titulo_neg", -10),
    ("reparacion", "titulo_neg", -10),
    ("arriendo", "titulo_neg", -10),

    ("lenovo", "producto", 5),
    ("thinkpad", "producto", 5),
    ("hp", "producto", 3),
    ("laserjet", "producto", 3),
]

REGLAS_ORGANISMOS = [
    # (Nombre del Organismo (exacto, en minúsculas), Puntos)
    ("ejercito de chile", 4),
    ("poder judicial", 4),
    ("armada de chile", 3),
]

# ----------------------------------------

def seed_keywords(session):
    """Puebla la tabla ca_keyword."""
    print("Poblando Keywords...")
    count = 0
    for keyword, tipo, puntos in REGLAS_KEYWORDS:
        # Verificar si ya existe
        stmt = select(CaKeyword).where(CaKeyword.keyword == keyword, CaKeyword.tipo == tipo)
        existe = session.scalars(stmt).first()

        if not existe:
            kw = CaKeyword(keyword=keyword, tipo=tipo, puntos=puntos)
            session.add(kw)
            count += 1

    session.commit()
    print(f"¡Keywords añadidas: {count}!")


def seed_organismos_prioritarios(session):
    """Puebla la tabla ca_organismo_prioritario."""
    print("Poblando Organismos Prioritarios...")
    count = 0
    for nombre_org, puntos in REGLAS_ORGANISMOS:
        nombre_org_norm = nombre_org.lower().strip()

        # 1. Buscar el ID del organismo en la tabla CaOrganismo
        stmt_org = select(CaOrganismo).where(CaOrganismo.nombre == nombre_org_norm)
        organismo = session.scalars(stmt_org).first()

        if not organismo:
            print(f"  ADVERTENCIA: No se encontró el organismo '{nombre_org_norm}'. "
                  f"Este organismo debe ser cargado primero por el scraper (ELT).")
            continue

        # 2. Verificar si ya es prioritario
        stmt_prio = select(CaOrganismoPrioritario).where(
            CaOrganismoPrioritario.organismo_id == organismo.organismo_id
        )
        existe = session.scalars(stmt_prio).first()

        if not existe:
            prio = CaOrganismoPrioritario(
                organismo_id=organismo.organismo_id, puntos=puntos
            )
            session.add(prio)
            count += 1

    session.commit()
    print(f"¡Organismos Prioritarios añadidos: {count}!")


if __name__ == "__main__":
    print("Iniciando siembra (seeding) de la base de datos...")
    session = SessionLocal()
    try:
        seed_keywords(session)
        # Nota: Es posible que seed_organismos falle si los organismos
        # aún no han sido creados por el scraper.
        # Se recomienda ejecutar el scraper una vez y luego este script.
        seed_organismos_prioritarios(session)
        print("¡Siembra completada!")
    except Exception as e:
        print(f"Error durante la siembra: {e}")
        session.rollback()
    finally:
        session.close()