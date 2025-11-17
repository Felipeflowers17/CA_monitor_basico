# -*- coding: utf-8 -*-
"""
Manejador de API (API Handler).
Valida y extrae datos de las respuestas JSON.
Adaptado para usar el logger centralizado.

"""
from typing import List, Dict
from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)


def validar_respuesta_api(datos: Dict) -> bool: 
    """Valida la estructura básica de la respuesta JSON."""
    try:
        if 'success' not in datos or datos['success'] != 'OK':
            logger.warning("Respuesta API sin 'success': 'OK'.")
            return False
        if 'payload' not in datos or 'resultados' not in datos['payload']:
            logger.warning("Respuesta API sin 'payload' o 'resultados'.")
            return False
        if not isinstance(datos['payload']['resultados'], list):
            logger.warning("Respuesta API 'resultados' no es una lista.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validando respuesta API: {e}")
        return False

def extraer_resultados(datos_json: Dict) -> List[Dict]: 
    """Extrae la lista de 'resultados' (compras) de la respuesta."""
    try:
        return datos_json['payload']['resultados']
    except (KeyError, TypeError) as e:
        logger.error(f"ERROR al extraer resultados: {e}")
        return []

def extraer_metadata_paginacion(datos_json: Dict) -> Dict: 
    """Extrae la metadata de paginación (total páginas, total resultados)."""
    default = {'resultCount': 0, 'pageCount': 0}
    try:
        payload = datos_json['payload']
        return {
            'resultCount': payload.get('resultCount', 0),
            'pageCount': payload.get('pageCount', 0)
        }
    except (KeyError, TypeError) as e:
        logger.error(f"ERROR al extraer metadata: {e}")
        return default