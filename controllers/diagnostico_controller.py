"""
diagnostico_controller.py — Controlador especializado para diagnóstico de conexiones de base de datos
Ubicación: controllers/diagnostico_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/DiagnosticoController.cs

Principios SOLID aplicados:
- SRP: Este controlador solo maneja diagnóstico de conexiones, nada más
- DIP: Depende de abstracciones (Protocol), no de implementaciones concretas
- OCP: Abierto para extensión (nuevos tipos de diagnóstico) sin modificar código existente
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from config import get_settings
from repositorios.repositorio_lectura_sqlserver import RepositorioLecturaSqlServer
from repositorios.repositorio_lectura_postgresql import RepositorioLecturaPostgreSQL
from repositorios.repositorio_lectura_mysql_mariadb import RepositorioLecturaMysqlMariaDB
from servicios.conexion.proveedor_conexion import ProveedorConexion


# Configurar logging (equivalente a ILogger<DiagnosticoController>)
logger = logging.getLogger(__name__)

# Crear el router (equivalente a [Route("api/diagnostico")])
router = APIRouter(
    prefix="/api/diagnostico",
    tags=["Diagnóstico"]
)


def _obtener_repositorio():
    """
    Factory que crea el repositorio según el proveedor configurado.
    
    Equivalente a la inyección de dependencias en ASP.NET Core.
    El contenedor DI en C# resuelve esto automáticamente según DatabaseProvider.
    """
    settings = get_settings()
    proveedor_conexion = ProveedorConexion()
    proveedor_bd = settings.database.provider.lower()
    
    if proveedor_bd == "postgres":
        return RepositorioLecturaPostgreSQL(proveedor_conexion)
    elif proveedor_bd in ("mysql", "mariadb"):
        return RepositorioLecturaMysqlMariaDB(proveedor_conexion)
    else:  # sqlserver, sqlserverexpress, localdb, o por defecto
        return RepositorioLecturaSqlServer(proveedor_conexion)


@router.get("/conexion")
async def obtener_diagnostico_conexion():
    """
    Obtiene información de diagnóstico sobre la conexión actual a la base de datos.
    
    Ruta: GET /api/diagnostico/conexion
    
    Equivalente a: DiagnosticoController.ObtenerDiagnosticoConexionAsync()
    
    FUNCIONAMIENTO:
    1. Delega al repositorio correspondiente según DatabaseProvider
    2. El repositorio ejecuta consultas específicas del motor de BD
    3. Devuelve información estructurada sin exponer credenciales
    
    INFORMACIÓN DEVUELTA (varía según el motor):
    - Nombre de la base de datos actual
    - Versión del motor de base de datos
    - Servidor/host conectado
    - Puerto de conexión
    - Hora de inicio del servidor (clave para distinguir Docker vs local)
    - Usuario conectado
    - ID del proceso/sesión
    
    NOTA DE SEGURIDAD:
    Este endpoint NO expone credenciales ni la cadena de conexión completa.
    Solo muestra metadatos públicos del servidor para propósitos de diagnóstico.
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info("INICIO diagnóstico de conexión")
        
        # Obtener proveedor configurado
        settings = get_settings()
        proveedor_configurado = settings.database.provider
        
        # OBTENER REPOSITORIO
        repositorio = _obtener_repositorio()
        
        # DELEGACIÓN AL REPOSITORIO (aplicando SRP y DIP)
        # El repositorio inyectado ya es el correcto según DatabaseProvider
        diagnostico = await repositorio.obtener_diagnostico_conexion()
        
        # LOGGING DE RESULTADO
        logger.info(
            "DIAGNÓSTICO exitoso - Proveedor: %s",
            proveedor_configurado
        )
        
        # CONSTRUCCIÓN DE RESPUESTA
        return {
            "estado": 200,
            "mensaje": "Diagnóstico de conexión obtenido exitosamente.",
            "servidor": diagnostico,
            "configuracion": {
                "proveedorConfigurado": proveedor_configurado,
                "descripcion": "Proveedor configurado en .env"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except NotImplementedError:
        # El repositorio actual no implementa diagnóstico
        settings = get_settings()
        proveedor = settings.database.provider
        
        logger.warning(
            "Diagnóstico no implementado para proveedor: %s",
            proveedor
        )
        
        raise HTTPException(
            status_code=501,
            detail={
                "estado": 501,
                "mensaje": f"El diagnóstico de conexión no está implementado para el proveedor '{proveedor}'.",
                "detalle": "Esta funcionalidad aún no está disponible para este motor de base de datos.",
                "proveedorConfigurado": proveedor
            }
        )
    
    except Exception as excepcion_general:
        # ERROR GENERAL NO ESPERADO
        logger.error(
            "ERROR CRÍTICO - Falla en diagnóstico de conexión",
            exc_info=True
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno al obtener diagnóstico de conexión.",
                "detalle": str(excepcion_general),
                "tipoError": type(excepcion_general).__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "sugerencia": "Revise los logs del servidor para más detalles."
            }
        )


# NOTAS PEDAGÓGICAS para el tutorial:
#
# 1. CONTROLADOR ESPECIALIZADO:
#    - Responsabilidad única: solo diagnóstico
#    - No mezcla con operaciones CRUD
#    - Fácil de mantener y extender
#
# 2. APLICACIÓN CORRECTA DE DIP:
#    - Depende de la abstracción (Protocol IRepositorioLecturaTabla)
#    - No conoce las implementaciones concretas directamente
#    - El factory _obtener_repositorio() resuelve la implementación correcta
#
# 3. ARQUITECTURA LIMPIA:
#    diagnostico_controller → IRepositorioLecturaTabla → Implementación específica
#    (Presentación)          (Abstracción)              (RepositorioLecturaPostgreSQL, etc.)
#
# 4. EXTENSIBILIDAD (OCP):
#    - Para agregar soporte a un nuevo motor de BD:
#      1. Crear repositorio_lectura_nuevo_motor.py : IRepositorioLecturaTabla
#      2. Implementar obtener_diagnostico_conexion()
#      3. Agregar case en _obtener_repositorio()
#      4. Este controlador funciona automáticamente
#
# 5. SIN ACOPLAMIENTO:
#    - No hay referencias directas a pyodbc, asyncpg, aiomysql
#    - Todo el código específico de BD está en los repositorios
#    - El controlador solo coordina HTTP ↔ Repositorio
