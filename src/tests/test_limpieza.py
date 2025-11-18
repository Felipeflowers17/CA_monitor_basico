# -*- coding: utf-8 -*-
"""
Tests unitarios para la Fase 3: Limpieza Automática (Housekeeping).
"""

from datetime import datetime, timedelta
from src.db.db_models import CaLicitacion, CaSeguimiento

def test_limpieza_automatica_logica(db_service, db_session):
    """
    Verifica que el método limpiar_registros_antiguos funciona correctamente.
    """
    
    # Definimos fechas
    hoy = datetime.now()
    hace_40_dias = hoy - timedelta(days=40)
    hace_10_dias = hoy - timedelta(days=10)

    # --- PREPARACIÓN DE DATOS ---
    
    # CASO 1: Basura (Vieja, Cerrada, No Favorita) -> DEBE BORRARSE
    ca_borrar = CaLicitacion(
        codigo_ca="BORRAR-01",
        nombre="Licitacion Vieja y Cerrada",
        estado_ca_texto="Cerrada",
        fecha_cierre=hace_40_dias,
        puntuacion_final=5
    )
    
    # CASO 2: Reciente (Nueva, Cerrada, No Favorita) -> DEBE QUEDARSE
    ca_reciente = CaLicitacion(
        codigo_ca="RECIENTE-01",
        nombre="Licitacion Reciente",
        estado_ca_texto="Cerrada",
        fecha_cierre=hace_10_dias,
        puntuacion_final=5
    )
    
    # CASO 3: Vigente (Vieja, Publicada, No Favorita) -> DEBE QUEDARSE
    ca_publicada = CaLicitacion(
        codigo_ca="PUBLICADA-01",
        nombre="Licitacion Vieja pero Publicada",
        estado_ca_texto="Publicada",
        fecha_cierre=hace_40_dias,
        puntuacion_final=5
    )
    
    # CASO 4: Protegida (Vieja, Cerrada, FAVORITA) -> DEBE QUEDARSE
    ca_favorita = CaLicitacion(
        codigo_ca="FAVORITA-01",
        nombre="Licitacion Favorita Vieja",
        estado_ca_texto="Cerrada",
        fecha_cierre=hace_40_dias,
        puntuacion_final=100
    )
    
    # Guardamos todo en la BD de prueba
    db_session.add_all([ca_borrar, ca_reciente, ca_publicada, ca_favorita])
    db_session.commit()
    
    # Guardamos los IDs en variables simples para usarlos después
    # (Esto evita el error DetachedInstanceError al intentar leer el objeto borrado)
    id_borrar = ca_borrar.ca_id
    id_reciente = ca_reciente.ca_id
    id_publicada = ca_publicada.ca_id
    id_favorita = ca_favorita.ca_id
    
    # Agregamos la marca de favorito al Caso 4
    fav_record = CaSeguimiento(ca_id=id_favorita, es_favorito=True)
    db_session.add(fav_record)
    db_session.commit()

    # --- EJECUCIÓN DEL TEST ---
    
    # Ejecutamos la limpieza configurada a 30 días
    registros_eliminados = db_service.limpiar_registros_antiguos(dias_retencion=30)
    
    # --- VERIFICACIÓN ---
    
    # 1. Verificar cantidad borrada
    assert registros_eliminados == 1, f"Debería borrar solo 1 registro, borró {registros_eliminados}"
    
    # 2. Verificar quién sobrevivió consultando por ID directo
    # Usamos db_session.get() que hace una consulta nueva limpia
    
    assert db_session.get(CaLicitacion, id_borrar) is None, "El CASO 1 (Basura) debería haber sido borrado."
    assert db_session.get(CaLicitacion, id_reciente) is not None, "El CASO 2 (Reciente) no debió borrarse."
    assert db_session.get(CaLicitacion, id_publicada) is not None, "El CASO 3 (Publicada) no debió borrarse."
    assert db_session.get(CaLicitacion, id_favorita) is not None, "El CASO 4 (Favorita) debió estar protegido."