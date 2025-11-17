# -*- coding: utf-8 -*-
"""
Servicio de Scraping (ScraperService).


"""

import time
from playwright.sync_api import sync_playwright, Page, Response
from typing import Optional, Dict, Callable, List

from src.utils.logger import configurar_logger

from . import api_handler
from .url_builder import (
    construir_url_listado,
    construir_url_ficha,
    construir_url_api_ficha
)
from config.config import (
    MODO_HEADLESS,
    TIMEOUT_REQUESTS,
    DELAY_ENTRE_PAGINAS,
    HEADERS_API
)

logger = configurar_logger('scraper_service')


class ScraperService:
    
    def __init__(self):
        logger.info("ScraperService inicializado (con lógica original).")

    def _scrapear_pagina_listado(
        self, page: Page, numero_pagina: int, accion_trigger: Callable[[], None]
    ) -> tuple:
        
        logger.debug(f"Configurando listener para API page_number={numero_pagina}...")
        try:
            predicate = lambda response: (
                'api.buscador.mercadopublico.cl/compra-agil' in response.url and
                f"page_number={numero_pagina}" in response.url and
                response.status == 200
            )
            with page.expect_response(predicate, timeout=TIMEOUT_REQUESTS * 1000) as response_info:
                logger.debug(f"Ejecutando acción trigger para página {numero_pagina}...")
                accion_trigger()
            
            logger.debug(f"Respuesta API específica para página {numero_pagina} recibida.")
            response = response_info.value
            datos_api = response.json()

            if not api_handler.validar_respuesta_api(datos_api):
                logger.error(f"Respuesta API inválida para página {numero_pagina}.")
                return False, {}, []

            metadata = api_handler.extraer_metadata_paginacion(datos_api)
            resultados = api_handler.extraer_resultados(datos_api)
            
            logger.info(f"Página {numero_pagina} procesada: {len(resultados)} compras encontradas.")
            
            return True, metadata, resultados

        except Exception as e:
            if "Timeout" in str(e):
                logger.error(f"TIMEOUT en página {numero_pagina}. La API (page_number={numero_pagina}) no respondió.")
            else:
                logger.error(f"ERROR crítico al scrapear página {numero_pagina}: {e}")
            return False, {}, []

    def run_scraper_listado(
        self,
        progress_callback: Callable[[str], None], 
        filtros: Optional[Dict] = None,
        max_paginas: Optional[int] = None
    ) -> List[Dict]:
        
        logger.info("="*60)
        logger.info("INICIANDO SCRAPER DE LISTADO (Lógica Original)")
        
        tiempo_inicio = time.time()
        total_compras_procesadas = 0
        paginas_procesadas = 0
        limite = max_paginas if max_paginas is not None else 0
        todas_las_compras = []
        
        with sync_playwright() as p:
            try:
                progress_callback("Iniciando navegador (Fase 1)...") 
                browser = p.chromium.launch(headless=MODO_HEADLESS, slow_mo=500)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit(537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='es-CL'
                )
                page = context.new_page()
                page.set_extra_http_headers(HEADERS_API) 
                
                url_pagina_1 = construir_url_listado(1, filtros)
                logger.info(f"Navegando a página 1: {url_pagina_1}")
                progress_callback("Cargando página 1...") 
                
                accion_p1 = lambda: page.goto(url_pagina_1, wait_until='networkidle')
                exito, metadata, resultados = self._scrapear_pagina_listado(page, 1, accion_p1)
                
                if not exito:
                    raise Exception("No se pudo obtener la página 1. Abortando.")
                
                total_paginas = metadata.get('pageCount', 0)
                total_compras_procesadas += len(resultados)
                todas_las_compras.extend(resultados)
                paginas_procesadas += 1

                limite = total_paginas
                if max_paginas is not None and max_paginas > 0 and max_paginas < total_paginas:
                    limite = max_paginas
                
                logger.info(f"Límite de páginas establecido en: {limite}")
                progress_callback(f"Página 1/{limite} procesada. Total páginas: {total_paginas}") 

                for num_pagina in range(2, limite + 1):
                    time.sleep(DELAY_ENTRE_PAGINAS)
                    
                    logger.info(f"--- Procesando Página {num_pagina} ---")
                    progress_callback(f"Procesando página {num_pagina}/{limite}...") 
                    
                    selector_aria_label = "Go to next page"
                    selector_pagina_siguiente = page.locator(f'button[aria-label="{selector_aria_label}"]')

                    try:
                        selector_pagina_siguiente.wait_for(state='visible', timeout=10000)
                    except Exception as e:
                        logger.error(f"No se pudo encontrar el paginador 'Siguiente Página'. Abortando bucle.")
                        progress_callback("Error: No se encontró botón 'Siguiente'. Saltando.") 
                        break
                    
                    accion_clic = lambda: selector_pagina_siguiente.click()
                    exito, _, resultados_pagina = self._scrapear_pagina_listado(page, num_pagina, accion_clic)
                    
                    if exito:
                        total_compras_procesadas += len(resultados_pagina)
                        todas_las_compras.extend(resultados_pagina)
                        paginas_procesadas += 1
                    else:
                        logger.warning(f"Se omite la página {num_pagina} por error de API.")
                
                context.close()
                browser.close()
                logger.info("Navegador (Playwright) cerrado.")
                
                if todas_las_compras:
                    logger.info("Limpiando duplicados de la lista cruda...")
                    codigos_conteo = {}
                    for compra in todas_las_compras:
                        codigo = compra.get('codigo', compra.get('id'))
                        if codigo:
                            codigos_conteo[codigo] = codigos_conteo.get(codigo, 0) + 1
                    compras_unicas = {}
                    for compra in todas_las_compras:
                        codigo = compra.get('codigo', compra.get('id'))
                        if codigo and codigo not in compras_unicas:
                            compras_unicas[codigo] = compra
                    
                    lista_unicas = list(compras_unicas.values())
                    logger.info(f"Scraping crudo finalizado. {len(lista_unicas)} compras únicas encontradas.")
                    
                    return lista_unicas

            except Exception as e:
                logger.critical(f"FALLO EL PROCESO DE SCRAPING (Fase 1): {e}")
                progress_callback(f"Error Fase 1: {e}") 
                raise e
            finally:
                tiempo_total = time.time() - tiempo_inicio
                logger.info(f"Resumen Fase 1: {total_compras_procesadas} compras procesadas.")
                
        return []

    def scrape_ficha_detalle_api(
        self,
        page: Page,
        codigo_ca: str,
        progress_callback: Callable[[str], None] 
    ) -> Optional[Dict]:
        
        url_api_ficha = construir_url_api_ficha(codigo_ca)
        url_web_ficha = construir_url_ficha(codigo_ca)
        
        logger.info(f"[Fase 2] Scrapeando Ficha: {url_web_ficha}")

        def log_all_responses(response: Response):
            status = response.status
            url = response.url
            if "api.buscador.mercadopublico.cl" in url:
                logger.warning(f"DEBUG-SCRAPER: API Detectada (Status: {status}) -> {url}")
            else:
                logger.debug(f"DEBUG-SCRAPER: Recurso (Status: {status}) -> {url}")
        
        page.on("response", log_all_responses)

        try:
            predicate = lambda response: (
                url_api_ficha in response.url and
                response.status == 200
            )
            with page.expect_response(predicate, timeout=TIMEOUT_REQUESTS * 1000) as response_info:
                logger.debug(f"[{codigo_ca}] Navegando a la ficha web para triggerear la API...")
                page.goto(url_web_ficha, wait_until='load')
            
            logger.debug(f"[{codigo_ca}] Respuesta API de Ficha (predicate) recibida.")
            response = response_info.value
            datos_api_ficha = response.json()

            if 'success' not in datos_api_ficha or datos_api_ficha['success'] != 'OK':
                logger.warning(f"[{codigo_ca}] Respuesta API de Ficha sin 'success': 'OK'.")
                return None
            
            if 'payload' not in datos_api_ficha:
                logger.warning(f"[{codigo_ca}] Respuesta API de Ficha sin 'payload'.")
                return None

            payload = datos_api_ficha['payload']
            
            # Ahora extraemos todos los campos que necesitamos actualizar en la BD.
            datos_extraidos = {
                'descripcion': payload.get('descripcion'),
                'direccion_entrega': payload.get('direccion_entrega'),
                'fecha_cierre_p1': payload.get('fecha_cierre_primer_llamado'),
                'fecha_cierre_p2': payload.get('fecha_cierre_segundo_llamado'),
                'productos_solicitados': payload.get('productos_solicitados', []),
                'estado': payload.get('estado'), 
                'cantidad_provedores_cotizando': payload.get('cantidad_provedores_cotizando') 
            }

            
            logger.info(f"[{codigo_ca}] Ficha procesada. Productos encontrados: {len(datos_extraidos['productos_solicitados'])}")
            return datos_extraidos

        except Exception as e:
            if "Timeout" in str(e):
                logger.error(f"[{codigo_ca}] TIMEOUT en Ficha Individual. La API no respondió a tiempo.")
                logger.error(f"[{codigo_ca}] Revisa los logs 'DEBUG-SCRAPER' de arriba para ver si la URL de la API ha cambiado o si devolvió un error (ej. 403, 500).")
            else:
                logger.error(f"[{codigo_ca}] ERROR crítico al scrapear Ficha Individual: {e}")
            return None
        finally:
            page.remove_listener("response", log_all_responses)