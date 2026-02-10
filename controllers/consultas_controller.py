"""
consultas_controller.py — Controlador específico para ejecutar consultas SQL parametrizadas
Ubicación: controllers/consultas_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/ConsultasController.cs

Principios SOLID aplicados:
- SRP: El controlador solo coordina peticiones HTTP para consultas SQL
- DIP: Depende de IServicioConsultas (abstracción), no de implementación concreta
- ISP: Consume solo los métodos necesarios de IServicioConsultas
- OCP: Preparado para agregar más endpoints sin modificar código existente

Diferencias con EntidadesController:
- EntidadesController: Operaciones CRUD estándar sobre tablas (SELECT * FROM tabla)
- ConsultasController: Consultas SQL personalizadas con parámetros y lógica compleja
"""

import logging
from typing import Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from config import get_settings
from servicios.servicio_consultas import ServicioConsultas
from servicios.conexion.proveedor_conexion import ProveedorConexion
from repositorios import (
    RepositorioConsultasSqlServer,
    RepositorioConsultasPostgreSQL,
    RepositorioConsultasMysqlMariaDB
)


# Crear router con prefijo y tags
router = APIRouter(
    prefix="/api/consultas",
    tags=["Consultas SQL"]
)

# Logger para auditoría
logger = logging.getLogger(__name__)


# ================================================================
# MODELO DE SOLICITUD
# ================================================================
class SolicitudConsulta(BaseModel):
    """
    Modelo para el body de la petición de consulta SQL parametrizada.

    Ejemplo:
    {
        "consulta": "SELECT * FROM productos WHERE precio > @precio",
        "parametros": {
            "precio": 100
        }
    }
    """
    consulta: str
    parametros: dict[str, Any] | None = None


# ================================================================
# DEPENDENCIA: Obtener servicio de consultas
# ================================================================
def obtener_servicio_consultas() -> ServicioConsultas:
    """
    Crea y retorna el servicio de consultas con el repositorio apropiado.

    Esta función actúa como factory para inyección de dependencias.
    Determina el repositorio a usar según el proveedor configurado.
    """
    settings = get_settings()
    proveedor = ProveedorConexion(settings)
    proveedor_actual = proveedor.proveedor_actual

    # Seleccionar repositorio según proveedor
    if proveedor_actual == "postgres":
        repositorio = RepositorioConsultasPostgreSQL(proveedor)
    elif proveedor_actual in ("mysql", "mariadb"):
        repositorio = RepositorioConsultasMysqlMariaDB(proveedor)
    elif proveedor_actual in ("sqlserver", "sqlserverexpress", "localdb"):
        repositorio = RepositorioConsultasSqlServer(proveedor)
    else:
        # Por defecto, SQL Server
        repositorio = RepositorioConsultasSqlServer(proveedor)

    return ServicioConsultas(repositorio)


# ================================================================
# ENDPOINT: Ejecutar consulta parametrizada
# ================================================================
@router.post("/ejecutarconsultaparametrizada")
async def ejecutar_consulta_parametrizada(
    solicitud: SolicitudConsulta,
    servicio: ServicioConsultas = Depends(obtener_servicio_consultas)
):
    """
    Endpoint principal para ejecutar consultas SQL parametrizadas de forma segura.

    Ruta completa: POST /api/consultas/ejecutarconsultaparametrizada

    Formato de entrada JSON esperado:
    ```json
    {
        "consulta": "SELECT * FROM productos WHERE precio > @precio AND categoria = @categoria",
        "parametros": {
            "precio": 100,
            "categoria": "Electronics"
        }
    }
    ```

    Validaciones de seguridad aplicadas:
    - Solo consultas SELECT (previene modificaciones accidentales)
    - Tablas prohibidas según configuración
    - Parámetros seguros (previene inyección SQL)

    Returns:
        - 200 OK: Consulta ejecutada exitosamente con datos
        - 400 Bad Request: Formato de entrada inválido
        - 403 Forbidden: Consulta viola políticas de seguridad
        - 404 Not Found: Consulta exitosa pero sin resultados
        - 500 Internal Server Error: Error técnico
    """
    maximo_registros = 10000

    try:
        # ==============================================================================
        # FASE 1: VALIDACIÓN BÁSICA DE FORMATO DE ENTRADA
        # ==============================================================================
        if not solicitud.consulta or not solicitud.consulta.strip():
            raise HTTPException(
                status_code=400,
                detail="La consulta no puede estar vacía."
            )

        # ==============================================================================
        # FASE 2: LOGGING DE AUDITORÍA
        # ==============================================================================
        consulta_log = solicitud.consulta[:100] + "..." if len(solicitud.consulta) > 100 else solicitud.consulta
        logger.info(
            "INICIO ejecución consulta SQL - Consulta: %s, Parámetros: %d",
            consulta_log,
            len(solicitud.parametros) if solicitud.parametros else 0
        )

        # ==============================================================================
        # FASE 3: DELEGACIÓN AL SERVICIO (APLICANDO SRP y DIP)
        # ==============================================================================
        resultado = await servicio.ejecutar_consulta_parametrizada_desde_json(
            solicitud.consulta,
            solicitud.parametros
        )

        # ==============================================================================
        # FASE 4: LOGGING DE RESULTADOS
        # ==============================================================================
        logger.info(
            "ÉXITO ejecución consulta SQL - Registros obtenidos: %d",
            len(resultado)
        )

        # ==============================================================================
        # FASE 5: MANEJO DE CASO SIN RESULTADOS (404 NOT FOUND)
        # ==============================================================================
        if len(resultado) == 0:
            logger.info("SIN DATOS - Consulta ejecutada correctamente pero no devolvió registros")
            raise HTTPException(
                status_code=404,
                detail="La consulta se ejecutó correctamente pero no devolvió resultados."
            )

        # ==============================================================================
        # FASE 6: RESPUESTA EXITOSA CON DATOS Y METADATOS (200 OK)
        # ==============================================================================
        return {
            "Resultados": resultado,
            "Total": len(resultado),
            "Advertencia": f"Se alcanzó el límite de {maximo_registros} registros." if len(resultado) == maximo_registros else None
        }

    # ==============================================================================
    # MANEJO DE ERRORES ESTRATIFICADO POR TIPO DE EXCEPCIÓN
    # ==============================================================================

    except HTTPException:
        # Re-lanzar excepciones HTTP sin modificar
        raise

    except PermissionError as exc_acceso:
        # ERRORES DE POLÍTICA DE SEGURIDAD (403 FORBIDDEN)
        logger.warning(
            "ACCESO DENEGADO - Consulta rechazada por políticas de seguridad: %s",
            str(exc_acceso)
        )
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado por políticas de seguridad.",
                "detalle": str(exc_acceso),
                "sugerencia": "Verifique que la consulta cumple con las políticas de seguridad configuradas"
            }
        )

    except ValueError as exc_argumento:
        # ERRORES DE VALIDACIÓN DE ENTRADA (400 BAD REQUEST)
        logger.warning(
            "PARÁMETROS INVÁLIDOS - Formato de entrada incorrecto: %s",
            str(exc_argumento)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros de entrada inválidos.",
                "detalle": str(exc_argumento),
                "sugerencia": "Verifique el formato de la consulta y los nombres de parámetros"
            }
        )

    except Exception as exc_general:
        # ERRORES INESPERADOS/CRÍTICOS (500 INTERNAL SERVER ERROR)
        logger.error(
            "ERROR CRÍTICO - Falla inesperada ejecutando consulta SQL: %s",
            str(exc_general),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al ejecutar consulta SQL.",
                "tipoError": type(exc_general).__name__,
                "detalle": str(exc_general),
                "timestamp": datetime.utcnow().isoformat(),
                "sugerencia": "Revise los logs del servidor para más detalles."
            }
        )


# ================================================================
# NOTAS PEDAGÓGICAS
# ================================================================
#
# 1. CONTROLADOR ESPECIALIZADO VS GENÉRICO:
#    - EntidadesController: CRUD estándar sobre tablas
#    - ConsultasController: Consultas SQL arbitrarias con validaciones
#
# 2. MANEJO DE ERRORES:
#    - PermissionError → 403 (políticas de seguridad)
#    - ValueError → 400 (parámetros mal formateados)
#    - Exception → 500 (errores técnicos)
#
# 3. FORMATO DE RESPUESTA:
#    {
#        "Resultados": [...],
#        "Total": 42,
#        "Advertencia": null
#    }
