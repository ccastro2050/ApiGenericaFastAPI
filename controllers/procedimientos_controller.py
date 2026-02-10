"""
procedimientos_controller.py — Controlador específico para ejecutar procedimientos almacenados
Ubicación: controllers/procedimientos_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/ProcedimientosController.cs

Principios SOLID aplicados:
- SRP: El controlador solo coordina peticiones HTTP para procedimientos almacenados
- DIP: Depende de ServicioConsultas (abstracción), no de implementación concreta
- ISP: Consume solo los métodos necesarios de ServicioConsultas
- OCP: Preparado para agregar más endpoints sin modificar código existente

Diferencias con ConsultasController:
- ConsultasController: Consultas SQL SELECT arbitrarias con validaciones estrictas
- ProcedimientosController: Procedimientos almacenados que pueden hacer INSERT/UPDATE/DELETE
"""

import logging
from typing import Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query

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
    prefix="/api/procedimientos",
    tags=["Procedimientos Almacenados"]
)

# Logger para auditoría
logger = logging.getLogger(__name__)


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
# ENDPOINT: Ejecutar procedimiento almacenado
# ================================================================
@router.post("/ejecutarsp")
async def ejecutar_procedimiento_almacenado(
    parametros_sp: dict[str, Any],
    campos_encriptar: str | None = Query(default=None, description="Campos a encriptar, separados por coma"),
    servicio: ServicioConsultas = Depends(obtener_servicio_consultas)
):
    """
    Endpoint para ejecutar procedimientos almacenados con parámetros opcionales.

    Ruta completa: POST /api/procedimientos/ejecutarsp

    Formato de entrada JSON esperado:
    ```json
    {
        "nombreSP": "select_json_entity",
        "p_table_name": "usuario",
        "mensaje": "",
        "where_condition": null,
        "order_by": null,
        "limit_clause": null,
        "json_params": "{}",
        "select_columns": "*"
    }
    ```

    Parámetros:
    - parametros_sp: Diccionario con nombreSP y parámetros del procedimiento
    - campos_encriptar: Campos que deben ser encriptados, separados por coma (opcional)

    Returns:
        - 200 OK: Procedimiento ejecutado exitosamente con datos
        - 400 Bad Request: Formato de entrada inválido o nombreSP faltante
        - 500 Internal Server Error: Error técnico
    """
    try:
        # ==============================================================================
        # FASE 1: VALIDACIÓN DE ENTRADA
        # ==============================================================================
        if not parametros_sp or "nombreSP" not in parametros_sp:
            raise HTTPException(
                status_code=400,
                detail="El parámetro 'nombreSP' es requerido."
            )

        nombre_sp = str(parametros_sp["nombreSP"])

        if not nombre_sp or not nombre_sp.strip():
            raise HTTPException(
                status_code=400,
                detail="El parámetro 'nombreSP' no puede estar vacío."
            )

        # ==============================================================================
        # FASE 2: PROCESAMIENTO DE CAMPOS A ENCRIPTAR
        # ==============================================================================
        campos_a_encriptar: list[str] = []
        if campos_encriptar and campos_encriptar.strip():
            campos_a_encriptar = [c.strip() for c in campos_encriptar.split(",")]

        # ==============================================================================
        # FASE 3: PREPARAR PARÁMETROS (EXCLUIR nombreSP)
        # ==============================================================================
        parametros_limpios: dict[str, Any] = {}
        for clave, valor in parametros_sp.items():
            if clave.lower() != "nombresp":
                parametros_limpios[clave] = valor

        # ==============================================================================
        # FASE 4: LOGGING DE AUDITORÍA
        # ==============================================================================
        logger.info(
            "INICIO ejecución SP - Procedimiento: %s, Parámetros: %d",
            nombre_sp,
            len(parametros_limpios)
        )

        # ==============================================================================
        # FASE 5: DELEGACIÓN AL SERVICIO
        # ==============================================================================
        resultado = await servicio.ejecutar_procedimiento_almacenado(
            nombre_sp,
            parametros_limpios,
            campos_a_encriptar
        )

        # ==============================================================================
        # FASE 6: NORMALIZAR NOMBRES DE COLUMNA A LOWERCASE
        # ==============================================================================
        lista_normalizada = []
        for fila in resultado:
            fila_normalizada = {
                clave.lower(): valor
                for clave, valor in fila.items()
            }
            lista_normalizada.append(fila_normalizada)

        # ==============================================================================
        # FASE 7: LOGGING DE RESULTADO
        # ==============================================================================
        logger.info(
            "ÉXITO ejecución SP - Procedimiento: %s, Registros: %d",
            nombre_sp,
            len(lista_normalizada)
        )

        # ==============================================================================
        # FASE 8: RESPUESTA EXITOSA
        # ==============================================================================
        return {
            "Procedimiento": nombre_sp,
            "Resultados": lista_normalizada,
            "Total": len(lista_normalizada),
            "Mensaje": "Procedimiento ejecutado correctamente"
        }

    # ==============================================================================
    # MANEJO DE ERRORES ESTRATIFICADO POR TIPO DE EXCEPCIÓN
    # ==============================================================================

    except HTTPException:
        # Re-lanzar excepciones HTTP sin modificar
        raise

    except ValueError as exc_argumento:
        # ERRORES DE VALIDACIÓN DE ENTRADA (400 BAD REQUEST)
        logger.warning(
            "PARÁMETROS INVÁLIDOS - SP: %s",
            str(exc_argumento)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros de entrada inválidos.",
                "detalle": str(exc_argumento)
            }
        )

    except Exception as exc_general:
        # ERRORES INESPERADOS/CRÍTICOS (500 INTERNAL SERVER ERROR)
        logger.error(
            "ERROR CRÍTICO - Falla inesperada ejecutando SP: %s",
            str(exc_general),
            exc_info=True
        )

        # Construir mensaje de error más informativo para debugging
        detalle_error = []
        detalle_error.append(f"Tipo de error: {type(exc_general).__name__}")
        detalle_error.append(f"Mensaje: {str(exc_general)}")

        if hasattr(exc_general, "__cause__") and exc_general.__cause__:
            detalle_error.append(f"Error interno: {str(exc_general.__cause__)}")

        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al ejecutar procedimiento almacenado.",
                "tipoError": type(exc_general).__name__,
                "detalle": str(exc_general),
                "detalleCompleto": "\n".join(detalle_error),
                "timestamp": datetime.utcnow().isoformat(),
                "sugerencia": "Revise los logs del servidor para más detalles."
            }
        )


# ================================================================
# NOTAS PEDAGÓGICAS
# ================================================================
#
# 1. DIFERENCIA CON CONSULTASCONTROLLER:
#    - ConsultasController: Solo SELECT con validaciones estrictas
#    - ProcedimientosController: SPs que pueden hacer INSERT/UPDATE/DELETE
#
# 2. FORMATO DE RESPUESTA:
#    {
#        "Procedimiento": "nombre_sp",
#        "Resultados": [...],
#        "Total": 42,
#        "Mensaje": "Procedimiento ejecutado correctamente"
#    }
#
# 3. NORMALIZACIÓN:
#    - Nombres de columna se convierten a lowercase para compatibilidad
