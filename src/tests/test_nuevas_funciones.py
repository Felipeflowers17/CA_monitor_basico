# -*- coding: utf-8 -*-
"""
Tests unitarios para las nuevas funcionalidades (Notas y Segundo Llamado).
"""

from src.db.db_models import CaLicitacion, CaSeguimiento
from datetime import datetime

def test_guardar_segundo_llamado(db_service):
    """
    Prueba que el campo 'estado_convocatoria' se guarde correctamente
    cuando simulamos una carga de datos (Fase 1).
    """
    # 1. Preparamos datos simulados (como si vinieran del Scraper)
    datos_raw = [{
        "codigo": "123-TEST-2L",
        "nombre": "Licitación de Prueba",
        "organismo": "Hospital Test",
        "unidad": "Adquisiciones",
        "estado": "Publicada",
        "fecha_cierre": datetime.now(),
        "estado_convocatoria": 2  # <--- El dato clave: ES UN SEGUNDO LLAMADO
    }]

    # 2. Ejecutamos el método de inserción
    db_service.insertar_o_actualizar_licitaciones_raw(datos_raw)

    # 3. Verificamos que se guardó en la BD
    licitaciones = db_service.obtener_todas_candidatas_fase_1_para_recalculo()
    licitacion = licitaciones[0]

    assert licitacion.codigo_ca == "123-TEST-2L"
    assert licitacion.estado_convocatoria == 2, "El estado debería ser 2 (Segundo Llamado)"

def test_guardar_y_editar_notas(db_service, db_session):
    """
    Prueba el flujo completo de notas.
    CORREGIDO: Usamos session.get() en lugar de refresh() para evitar problemas de sesiones.
    """
    # 1. Insertar una licitación base manualmente para probar
    datos_raw = [{
        "codigo": "NOTA-TEST-01",
        "nombre": "Compra con Nota",
        "organismo": "Muni Test",
    }]
    db_service.insertar_o_actualizar_licitaciones_raw(datos_raw)
    
    # Obtener el ID que se generó
    licitacion = db_service.obtener_todas_candidatas_fase_1_para_recalculo()[0]
    ca_id = licitacion.ca_id

    # 2. Agregar una nota inicial
    texto_nota = "Falta documentación bancaria"
    db_service.actualizar_nota_seguimiento(ca_id, texto_nota)

    # 3. Verificar en BD (Consulta fresca)
    seguimiento = db_session.get(CaSeguimiento, ca_id)
    assert seguimiento is not None
    assert seguimiento.notas == texto_nota
    assert seguimiento.es_favorito is False 

    # 4. Editar la nota
    texto_editado = "Documentación OK. Llamar a Pedro."
    db_service.actualizar_nota_seguimiento(ca_id, texto_editado)

    # 5. Verificar actualización (Forzamos nueva consulta limpiando la sesión)
    db_session.expire_all() 
    seguimiento_editado = db_session.get(CaSeguimiento, ca_id)
    assert seguimiento_editado.notas == texto_editado

def test_nota_no_borra_favorito(db_service, db_session):
    """
    Verifica que al agregar una nota a una licitación que YA era favorita,
    no se pierda el estado de favorito.
    """
    # 1. Crear licitación
    datos_raw = [{"codigo": "FAV-TEST-01", "nombre": "Compra Favorita"}]
    db_service.insertar_o_actualizar_licitaciones_raw(datos_raw)
    licitacion = db_service.obtener_todas_candidatas_fase_1_para_recalculo()[0]
    
    # 2. Marcar como favorito
    db_service.gestionar_favorito(licitacion.ca_id, True)
    
    # 3. Agregar nota
    db_service.actualizar_nota_seguimiento(licitacion.ca_id, "Nota importante")

    # 4. Verificar
    db_session.expire_all()
    seguimiento = db_session.get(CaSeguimiento, licitacion.ca_id)
    assert seguimiento.es_favorito is True, "Debería seguir siendo favorito"
    assert seguimiento.notas == "Nota importante"