"""
estructuras_controller.py — Controlador para introspección de base de datos
Ubicación: controllers/estructuras_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/EstructurasController.cs

Función: Permite consultar la estructura interna de la base de datos:
- Ver columnas de una tabla específica
- Obtener la estructura completa de la base de datos
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends, Query

from config import get_settings
from servicios.conexion.proveedor_conexion import ProveedorConexion
from repositorios import (
    RepositorioConsultasSqlServer,
    RepositorioConsultasPostgreSQL,
    RepositorioConsultasMysqlMariaDB
)


# Crear router con prefijo y tags
router = APIRouter(
    prefix="/api/estructuras",
    tags=["Estructuras BD"]
)

# Logger para auditoría
logger = logging.getLogger(__name__)


# ================================================================
# DEPENDENCIA: Obtener repositorio de consultas
# ================================================================
def obtener_repositorio_consultas():
    """
    Crea y retorna el repositorio de consultas apropiado según el proveedor.
    """
    settings = get_settings()
    proveedor = ProveedorConexion(settings)
    proveedor_actual = proveedor.proveedor_actual

    if proveedor_actual == "postgres":
        return RepositorioConsultasPostgreSQL(proveedor)
    elif proveedor_actual in ("mysql", "mariadb"):
        return RepositorioConsultasMysqlMariaDB(proveedor)
    elif proveedor_actual in ("sqlserver", "sqlserverexpress", "localdb"):
        return RepositorioConsultasSqlServer(proveedor)
    else:
        # Por defecto, SQL Server
        return RepositorioConsultasSqlServer(proveedor)


# ================================================================
# ENDPOINT: Obtener modelo/estructura de una tabla
# ================================================================
@router.get("/{nombre_tabla}/modelo")
async def obtener_modelo(
    nombre_tabla: str,
    esquema: str | None = Query(default=None, description="Esquema de la tabla (opcional)"),
    repositorio = Depends(obtener_repositorio_consultas)
):
    """
    Obtiene la estructura detallada de una tabla específica.

    Ruta: GET /api/estructuras/{nombre_tabla}/modelo

    Parámetros:
    - nombre_tabla: Nombre de la tabla a consultar
    - esquema: Esquema opcional (dbo, public, etc.)

    Retorna:
    - Columnas con sus tipos, constraints (PK, FK, UNIQUE), valores default, etc.

    Ejemplo de respuesta:
    ```json
    {
        "datos": [
            {
                "column_name": "id",
                "data_type": "int",
                "is_nullable": "NO",
                "is_primary_key": "YES",
                "is_identity": "YES"
            }
        ],
        "total": 5
    }
    ```
    """
    if not nombre_tabla or not nombre_tabla.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre de la tabla no puede estar vacío."
        )

    try:
        # Obtener el esquema real donde existe la tabla
        esquema_real = await repositorio.obtener_esquema_tabla(nombre_tabla, esquema)

        if not esquema_real:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la tabla '{nombre_tabla}' en ningún esquema."
            )

        # Obtener estructura de la tabla
        estructura = await repositorio.obtener_estructura_tabla(nombre_tabla, esquema_real)

        return {
            "datos": estructura,
            "total": len(estructura)
        }

    except HTTPException:
        raise

    except Exception as ex:
        logger.error("Error al obtener modelo de tabla %s: %s", nombre_tabla, str(ex))
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )


# ================================================================
# ENDPOINT: Obtener estructura completa de la base de datos
# ================================================================
@router.get("/basedatos")
async def obtener_estructura_base_datos(
    repositorio = Depends(obtener_repositorio_consultas)
):
    """
    Obtiene la estructura completa de la base de datos.

    Ruta: GET /api/estructuras/basedatos

    Retorna estructura completa incluyendo:
    - Tablas con columnas y constraints
    - Vistas
    - Procedimientos almacenados
    - Funciones
    - Triggers
    - Índices
    - Secuencias (PostgreSQL)
    - Tipos personalizados
    - Extensiones (PostgreSQL) / Eventos (MySQL)

    Ejemplo de respuesta:
    ```json
    {
        "tablas": [...],
        "vistas": [...],
        "procedimientos": [...],
        "funciones": [...],
        "triggers": [...],
        "indices": [...]
    }
    ```
    """
    try:
        estructura = await repositorio.obtener_estructura_completa_base_datos()
        return estructura

    except Exception as ex:
        logger.error("Error al obtener estructura de BD: %s", str(ex))
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )
