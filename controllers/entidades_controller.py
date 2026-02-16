"""
entidades_controller.py — Controlador genérico para operaciones HTTP sobre cualquier tabla
Ubicación: controllers/entidades_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/EntidadesController.cs

Principios SOLID aplicados:
- SRP: El controlador solo coordina peticiones HTTP, no contiene lógica de negocio
- DIP: Depende de abstracciones (Protocol), no de implementaciones concretas
- ISP: Consume solo los métodos necesarios del servicio
- OCP: Preparado para agregar más endpoints sin modificar código existente
"""

import logging
from typing import Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from servicios.fabrica_repositorios import crear_servicio_crud


# Configurar logging (equivalente a ILogger<EntidadesController>)
logger = logging.getLogger(__name__)

# Crear el router (equivalente a [Route("api/{tabla}")])
router = APIRouter(
    prefix="/api",
    tags=["Entidades"]
)


@router.get("/{tabla}")
async def listar(
    tabla: str,
    esquema: str | None = Query(default=None, description="Esquema de la base de datos"),
    limite: int | None = Query(default=None, description="Límite de registros a devolver")
):
    """
    Endpoint principal para listar registros de cualquier tabla.
    
    Ruta: GET /api/{tabla}?esquema={esquema}&limite={limite}
    
    Ejemplos:
    - GET /api/usuarios
    - GET /api/productos?limite=50
    - GET /api/pedidos?esquema=ventas&limite=100
    
    Equivalente a: EntidadesController.ListarAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO consulta - Tabla: %s, Esquema: %s, Límite: %s",
            tabla,
            esquema or "por defecto",
            limite or "por defecto"
        )
        
        # OBTENER SERVICIO (equivalente a inyección de dependencias)
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO (aplicando SRP y DIP)
        filas = await servicio.listar(tabla, esquema, limite)
        
        # LOGGING DE RESULTADOS
        logger.info(
            "RESULTADO exitoso - Registros obtenidos: %d de tabla %s",
            len(filas),
            tabla
        )
        
        # MANEJO DE CASO SIN DATOS (204 NO CONTENT)
        if len(filas) == 0:
            logger.info(
                "SIN DATOS - Tabla %s consultada exitosamente pero no contiene registros",
                tabla
            )
            return Response(status_code=204)
        
        # RESPUESTA EXITOSA CON DATOS Y METADATOS (200 OK)
        return {
            "tabla": tabla,
            "esquema": esquema or "por defecto",
            "limite": limite,
            "total": len(filas),
            "datos": filas
        }
    
    except ValueError as excepcion_argumento:
        # ERRORES DE VALIDACIÓN (400 BAD REQUEST)
        logger.warning(
            "ERROR DE VALIDACIÓN - Tabla: %s, Error: %s",
            tabla,
            str(excepcion_argumento)
        )
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros de entrada inválidos.",
                "detalle": str(excepcion_argumento),
                "tabla": tabla
            }
        )
    
    except PermissionError as excepcion_acceso:
        # ACCESO DENEGADO (403 FORBIDDEN)
        logger.warning(
            "ACCESO DENEGADO - Tabla restringida: %s, Error: %s",
            tabla,
            str(excepcion_acceso)
        )
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except LookupError as excepcion_operacion:
        # RECURSO NO ENCONTRADO (404 NOT FOUND)
        logger.error(
            "ERROR DE OPERACIÓN - Tabla: %s, Error: %s",
            tabla,
            str(excepcion_operacion)
        )
        raise HTTPException(
            status_code=404,
            detail={
                "estado": 404,
                "mensaje": "El recurso solicitado no fue encontrado.",
                "detalle": str(excepcion_operacion),
                "tabla": tabla,
                "sugerencia": "Verifique que la tabla y el esquema existan en la base de datos"
            }
        )
    
    except Exception as excepcion_general:
        # ERRORES CRÍTICOS (500 INTERNAL SERVER ERROR)
        logger.error(
            "ERROR CRÍTICO - Falla inesperada - Tabla: %s, Error: %s",
            tabla,
            str(excepcion_general),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al consultar tabla.",
                "tabla": tabla,
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat(),
                "sugerencia": "Revise los logs del servidor para más detalles."
            }
        )


@router.get("/{tabla}/{nombre_clave}/{valor}")
async def obtener_por_clave(
    tabla: str,
    nombre_clave: str,
    valor: str,
    esquema: str | None = Query(default=None, description="Esquema de la base de datos")
):
    """
    Obtiene registros filtrados por un valor de clave específico.
    
    Ruta: GET /api/{tabla}/{nombreClave}/{valor}
    Ejemplo: GET /api/factura/numero/1?esquema=ventas
    
    Equivalente a: EntidadesController.ObtenerPorClaveAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO filtrado - Tabla: %s, Esquema: %s, Clave: %s, Valor: %s",
            tabla,
            esquema or "por defecto",
            nombre_clave,
            valor
        )
        
        # OBTENER SERVICIO
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO
        filas = await servicio.obtener_por_clave(tabla, nombre_clave, valor, esquema)
        
        # LOGGING DE RESULTADOS
        logger.info(
            "RESULTADO filtrado - %d registros encontrados para %s=%s en %s",
            len(filas),
            nombre_clave,
            valor,
            tabla
        )
        
        # MANEJO DE CASO SIN DATOS (404)
        if len(filas) == 0:
            raise HTTPException(
                status_code=404,
                detail={
                    "estado": 404,
                    "mensaje": "No se encontraron registros",
                    "detalle": f"No se encontró ningún registro con {nombre_clave} = {valor} en la tabla {tabla}",
                    "tabla": tabla,
                    "esquema": esquema or "por defecto",
                    "filtro": f"{nombre_clave} = {valor}"
                }
            )
        
        # RESPUESTA EXITOSA
        return {
            "tabla": tabla,
            "esquema": esquema or "por defecto",
            "filtro": f"{nombre_clave} = {valor}",
            "total": len(filas),
            "datos": filas
        }
    
    except HTTPException:
        raise
    
    except PermissionError as excepcion_acceso:
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except ValueError as excepcion_argumento:
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros inválidos.",
                "detalle": str(excepcion_argumento),
                "tabla": tabla
            }
        )
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR CRÍTICO - Falla en filtrado - Tabla: %s, Clave: %s, Valor: %s",
            tabla,
            nombre_clave,
            valor,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al filtrar registros.",
                "tabla": tabla,
                "filtro": f"{nombre_clave} = {valor}",
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/{tabla}")
async def crear(
    tabla: str,
    datos_entidad: dict[str, Any],
    esquema: str | None = Query(default=None, description="Esquema de la base de datos"),
    campos_encriptar: str | None = Query(default=None, description="Campos a encriptar con BCrypt, separados por coma")
):
    """
    Crea un nuevo registro en la tabla especificada.
    
    Ruta: POST /api/{tabla}
    Ejemplo: POST /api/usuario con body JSON
    
    Equivalente a: EntidadesController.CrearAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO creación - Tabla: %s, Esquema: %s, Campos a encriptar: %s",
            tabla,
            esquema or "por defecto",
            campos_encriptar or "ninguno"
        )
        
        # VALIDACIÓN TEMPRANA
        if not datos_entidad:
            raise HTTPException(
                status_code=400,
                detail={
                    "estado": 400,
                    "mensaje": "Los datos de la entidad no pueden estar vacíos.",
                    "tabla": tabla
                }
            )
        
        # OBTENER SERVICIO
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO
        creado = await servicio.crear(tabla, datos_entidad, esquema, campos_encriptar)
        
        if creado:
            logger.info("ÉXITO creación - Registro creado en tabla %s", tabla)
            return {
                "estado": 200,
                "mensaje": "Registro creado exitosamente.",
                "tabla": tabla,
                "esquema": esquema or "por defecto"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "estado": 500,
                    "mensaje": "No se pudo crear el registro.",
                    "tabla": tabla
                }
            )
    
    except HTTPException:
        raise
    
    except PermissionError as excepcion_acceso:
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except ValueError as excepcion_argumento:
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Datos inválidos.",
                "detalle": str(excepcion_argumento),
                "tabla": tabla
            }
        )
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR CRÍTICO - Falla en creación - Tabla: %s",
            tabla,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al crear registro.",
                "tabla": tabla,
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.put("/{tabla}/{nombre_clave}/{valor_clave}")
async def actualizar(
    tabla: str,
    nombre_clave: str,
    valor_clave: str,
    datos_entidad: dict[str, Any],
    esquema: str | None = Query(default=None, description="Esquema de la base de datos"),
    campos_encriptar: str | None = Query(default=None, description="Campos a encriptar con BCrypt")
):
    """
    Actualiza un registro existente en la tabla especificada.
    
    Ruta: PUT /api/{tabla}/{nombreClave}/{valorClave}
    Ejemplo: PUT /api/usuario/email/juan@test.com con body JSON
    
    Equivalente a: EntidadesController.ActualizarAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO actualización - Tabla: %s, Clave: %s=%s, Esquema: %s, Campos a encriptar: %s",
            tabla,
            nombre_clave,
            valor_clave,
            esquema or "por defecto",
            campos_encriptar or "ninguno"
        )
        
        # VALIDACIÓN TEMPRANA
        if not datos_entidad:
            raise HTTPException(
                status_code=400,
                detail={
                    "estado": 400,
                    "mensaje": "Los datos de actualización no pueden estar vacíos.",
                    "tabla": tabla,
                    "filtro": f"{nombre_clave} = {valor_clave}"
                }
            )
        
        # OBTENER SERVICIO
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO
        filas_afectadas = await servicio.actualizar(
            tabla, nombre_clave, valor_clave, datos_entidad, esquema, campos_encriptar
        )
        
        if filas_afectadas > 0:
            logger.info(
                "ÉXITO actualización - %d filas actualizadas en tabla %s WHERE %s=%s",
                filas_afectadas,
                tabla,
                nombre_clave,
                valor_clave
            )
            return {
                "estado": 200,
                "mensaje": "Registro actualizado exitosamente.",
                "tabla": tabla,
                "esquema": esquema or "por defecto",
                "filtro": f"{nombre_clave} = {valor_clave}",
                "filasAfectadas": filas_afectadas,
                "camposEncriptados": campos_encriptar or "ninguno"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "estado": 404,
                    "mensaje": "No se encontró el registro a actualizar.",
                    "detalle": f"No existe un registro con {nombre_clave} = {valor_clave} en la tabla {tabla}",
                    "tabla": tabla,
                    "filtro": f"{nombre_clave} = {valor_clave}"
                }
            )
    
    except HTTPException:
        raise
    
    except PermissionError as excepcion_acceso:
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except ValueError as excepcion_argumento:
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros inválidos.",
                "detalle": str(excepcion_argumento),
                "tabla": tabla,
                "filtro": f"{nombre_clave} = {valor_clave}"
            }
        )
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR CRÍTICO - Falla en actualización - Tabla: %s, Clave: %s=%s",
            tabla,
            nombre_clave,
            valor_clave,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al actualizar registro.",
                "tabla": tabla,
                "filtro": f"{nombre_clave} = {valor_clave}",
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.delete("/{tabla}/{nombre_clave}/{valor_clave}")
async def eliminar(
    tabla: str,
    nombre_clave: str,
    valor_clave: str,
    esquema: str | None = Query(default=None, description="Esquema de la base de datos")
):
    """
    Elimina un registro existente de la tabla especificada.
    
    Ruta: DELETE /api/{tabla}/{nombreClave}/{valorClave}
    Ejemplo: DELETE /api/producto/codigo/PRD001
    
    Equivalente a: EntidadesController.EliminarAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO eliminación - Tabla: %s, Clave: %s=%s, Esquema: %s",
            tabla,
            nombre_clave,
            valor_clave,
            esquema or "por defecto"
        )
        
        # OBTENER SERVICIO
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO
        filas_eliminadas = await servicio.eliminar(tabla, nombre_clave, valor_clave, esquema)
        
        if filas_eliminadas > 0:
            logger.info(
                "ÉXITO eliminación - %d filas eliminadas de tabla %s WHERE %s=%s",
                filas_eliminadas,
                tabla,
                nombre_clave,
                valor_clave
            )
            return {
                "estado": 200,
                "mensaje": "Registro eliminado exitosamente.",
                "tabla": tabla,
                "esquema": esquema or "por defecto",
                "filtro": f"{nombre_clave} = {valor_clave}",
                "filasEliminadas": filas_eliminadas
            }
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "estado": 404,
                    "mensaje": "No se encontró el registro a eliminar.",
                    "detalle": f"No existe un registro con {nombre_clave} = {valor_clave} en la tabla {tabla}",
                    "tabla": tabla,
                    "filtro": f"{nombre_clave} = {valor_clave}"
                }
            )
    
    except HTTPException:
        raise
    
    except PermissionError as excepcion_acceso:
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except ValueError as excepcion_argumento:
        raise HTTPException(
            status_code=400,
            detail={
                "estado": 400,
                "mensaje": "Parámetros inválidos.",
                "detalle": str(excepcion_argumento),
                "tabla": tabla,
                "filtro": f"{nombre_clave} = {valor_clave}"
            }
        )
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR CRÍTICO - Falla en eliminación - Tabla: %s, Clave: %s=%s",
            tabla,
            nombre_clave,
            valor_clave,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno del servidor al eliminar registro.",
                "tabla": tabla,
                "filtro": f"{nombre_clave} = {valor_clave}",
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/{tabla}/verificar-contrasena")
async def verificar_contrasena(
    tabla: str,
    campo_usuario: str = Query(..., description="Nombre del campo de usuario"),
    campo_contrasena: str = Query(..., description="Nombre del campo de contraseña"),
    valor_usuario: str = Query(..., description="Valor del usuario"),
    valor_contrasena: str = Query(..., description="Contraseña a verificar"),
    esquema: str | None = Query(default=None, description="Esquema de la base de datos")
):
    """
    Verifica las credenciales de un usuario contra la base de datos.
    
    Ruta: POST /api/{tabla}/verificar-contrasena
    Ejemplo: POST /api/usuario/verificar-contrasena?campo_usuario=email&campo_contrasena=contrasena&valor_usuario=test@test.com&valor_contrasena=123456
    
    Equivalente a: EntidadesController.VerificarContrasenaAsync()
    """
    try:
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO verificación credenciales - Tabla: %s, Usuario: %s",
            tabla,
            valor_usuario
        )
        
        # OBTENER SERVICIO
        servicio = crear_servicio_crud()
        
        # DELEGACIÓN AL SERVICIO
        codigo, mensaje = await servicio.verificar_contrasena(
            tabla, campo_usuario, campo_contrasena, valor_usuario, valor_contrasena, esquema
        )
        
        # EVALUAR RESULTADO
        if codigo == 200:
            logger.info("Credenciales válidas para usuario: %s", valor_usuario)
            return {
                "estado": 200,
                "mensaje": mensaje,
                "usuario": valor_usuario
            }
        elif codigo == 404:
            raise HTTPException(
                status_code=404,
                detail={
                    "estado": 404,
                    "mensaje": mensaje,
                    "usuario": valor_usuario
                }
            )
        else:  # 401
            raise HTTPException(
                status_code=401,
                detail={
                    "estado": 401,
                    "mensaje": mensaje,
                    "usuario": valor_usuario
                }
            )
    
    except HTTPException:
        raise
    
    except PermissionError as excepcion_acceso:
        raise HTTPException(
            status_code=403,
            detail={
                "estado": 403,
                "mensaje": "Acceso denegado.",
                "detalle": str(excepcion_acceso),
                "tabla": tabla
            }
        )
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR CRÍTICO - Falla en verificación - Tabla: %s, Usuario: %s",
            tabla,
            valor_usuario,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno al verificar credenciales.",
                "tipoError": type(excepcion_general).__name__,
                "detalle": str(excepcion_general),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
