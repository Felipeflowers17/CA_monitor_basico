# -*- coding: utf-8 -*-
"""
Constructor de URLs (URL Builder).

"""
from typing import Dict, Optional
from config.config import URL_BASE_WEB, URL_BASE_API 

def construir_url_listado(numero_pagina: int = 1, filtros: Optional[Dict] = None):
    """
    Construye la URL para el listado de compras ágiles.
    """
    parametros = {
        'status': 2,
        'order_by': 'recent',
        'page_number': numero_pagina
    }

    if filtros:
        parametros.update(filtros)

    if 'region' not in parametros:
        parametros['region'] = 'all'

    string_parametros = '&'.join([f"{k}={v}" for k, v in parametros.items()])

    return f"{URL_BASE_WEB}/compra-agil?{string_parametros}"

def construir_url_ficha(codigo_compra: str):
    """
    Construye la URL para la ficha individual de una compra (página web).
    """
    return f"{URL_BASE_WEB}/ficha?code={codigo_compra}"

def construir_url_api_ficha(codigo_compra: str):
    """
    Construye la URL para la API de la ficha individual.
    """
    return f"{URL_BASE_API}/compra-agil?action=ficha&code={codigo_compra}"