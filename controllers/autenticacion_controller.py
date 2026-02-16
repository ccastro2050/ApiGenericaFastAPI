"""
autenticacion_controller.py — Controlador genérico que autentica usuarios y genera tokens JWT
Ubicación: controllers/autenticacion_controller.py

Equivalente a: ApiGenericaCsharp/Controllers/AutenticacionController.cs

Características:
- Compatible con cualquier tabla y campos personalizados
- Usa BCrypt para comparar contraseñas encriptadas
- Genera tokens JWT configurables desde .env
- No depende del tipo de base de datos (SQL Server, PostgreSQL, etc.)
- Sigue principios SOLID: SRP, DIP y OCP
"""

import logging
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from servicios.fabrica_repositorios import crear_servicio_crud


# Configurar logging (equivalente a ILogger<AutenticacionController>)
logger = logging.getLogger(__name__)

# Crear el router (equivalente a [Route("api/[controller]")])
router = APIRouter(
    prefix="/api/autenticacion",
    tags=["Autenticación"]
)


# ---------------------------------------------------------
# CLASE AUXILIAR: CredencialesGenericas
# ---------------------------------------------------------
# Representa el cuerpo del POST enviado por el cliente.
# Incluye toda la información necesaria para validar un usuario
# contra cualquier tabla de la base de datos.
#
# Equivalente a la clase CredencialesGenericas dentro de AutenticacionController.cs
class CredencialesGenericas(BaseModel):
    """
    Modelo para las credenciales de autenticación.
    """
    # Nombre de la tabla que contiene los usuarios
    # Ejemplo: "usuario", "vendedor", "cliente"
    tabla: str = Field(default="")
    
    # Nombre del campo que almacena el identificador de usuario
    # Ejemplo: "email", "nombre", "login"
    campoUsuario: str = Field(default="")
    
    # Nombre del campo que almacena la contraseña
    # Ejemplo: "clave", "password", "contrasena"
    campoContrasena: str = Field(default="")
    
    # Valor del usuario que intenta autenticarse
    usuario: str = Field(default="")
    
    # Contraseña enviada por el usuario (texto plano para comparar con hash en BD)
    contrasena: str = Field(default="")


# ---------------------------------------------------------
# POST: /api/autenticacion/token
# Descripción:
#   - Verifica credenciales en la tabla indicada (con hash BCrypt)
#   - Si son válidas, genera un token JWT con los datos básicos.
# ---------------------------------------------------------
@router.post("/token")
async def generar_token(credenciales: CredencialesGenericas):
    """
    Genera un token JWT si las credenciales son válidas.
    
    Ruta: POST /api/autenticacion/token
    
    Equivalente a: AutenticacionController.GenerarToken()
    """
    try:
        # -----------------------------------------------------
        # VALIDACIONES BÁSICAS DEL BODY
        # -----------------------------------------------------
        if (not credenciales.tabla or 
            not credenciales.campoUsuario or 
            not credenciales.campoContrasena or 
            not credenciales.usuario or 
            not credenciales.contrasena):
            
            raise HTTPException(
                status_code=400,
                detail={
                    "estado": 400,
                    "mensaje": "Debe enviar tabla, campos y credenciales completas.",
                    "ejemplo": {
                        "tabla": "TablaDeUsuarios",
                        "campoUsuario": "ejemploCampoUsuario",
                        "campoContrasena": "ejemploCampoContrasena",
                        "usuario": "ejemplo@correo.com",
                        "contrasena": "admin123"
                    }
                }
            )
        
        # LOGGING DE AUDITORÍA
        logger.info(
            "INICIO autenticación - Tabla: %s, Usuario: %s",
            credenciales.tabla,
            credenciales.usuario
        )
        
        # OBTENER SERVICIO Y CONFIGURACIÓN
        servicio = crear_servicio_crud()
        settings = get_settings()
        
        # -----------------------------------------------------
        # FASE 1: VERIFICACIÓN DE CREDENCIALES ENCRIPTADAS
        # -----------------------------------------------------
        # Se delega la comparación de contraseñas al ServicioCrud,
        # el cual implementa la lógica de verificación usando BCrypt.
        codigo, mensaje = await servicio.verificar_contrasena(
            nombre_tabla=credenciales.tabla,
            campo_usuario=credenciales.campoUsuario,
            campo_contrasena=credenciales.campoContrasena,
            valor_usuario=credenciales.usuario,
            valor_contrasena=credenciales.contrasena,
            esquema=None
        )
        
        # -----------------------------------------------------
        # FASE 2: EVALUACIÓN DEL RESULTADO DE VERIFICACIÓN
        # -----------------------------------------------------
        if codigo == 404:
            raise HTTPException(
                status_code=404,
                detail={"estado": 404, "mensaje": "Usuario no encontrado."}
            )
        
        if codigo == 401:
            raise HTTPException(
                status_code=401,
                detail={"estado": 401, "mensaje": "Contraseña incorrecta."}
            )
        
        if codigo != 200:
            raise HTTPException(
                status_code=500,
                detail={
                    "estado": 500,
                    "mensaje": "Error interno durante la verificación.",
                    "detalle": mensaje
                }
            )
        
        # -----------------------------------------------------
        # FASE 3: GENERACIÓN DEL TOKEN JWT
        # -----------------------------------------------------
        # Si la verificación fue exitosa, se crea un token JWT
        # con los datos básicos del usuario.
        
        # Duración configurable del token (en minutos)
        duracion = settings.jwt.duracion_minutos if settings.jwt.duracion_minutos > 0 else 60
        expiracion = datetime.utcnow() + timedelta(minutes=duracion)
        
        # Claims (datos del usuario dentro del token)
        # Equivalente a los claims en C#
        payload = {
            "sub": credenciales.usuario,                    # ClaimTypes.Name
            "tabla": credenciales.tabla,                    # Tabla usada para autenticación
            "campoUsuario": credenciales.campoUsuario,      # Campo de usuario utilizado
            "iss": settings.jwt.issuer,                     # Issuer (emisor)
            "aud": settings.jwt.audience,                   # Audience (audiencia)
            "exp": expiracion,                              # Fecha de expiración
            "iat": datetime.utcnow()                        # Issued at (fecha de emisión)
        }
        
        # Generar el token firmado con HMAC-SHA256
        # Equivalente a: new JwtSecurityTokenHandler().WriteToken(token)
        token_generado = jwt.encode(
            payload,
            settings.jwt.key,
            algorithm="HS256"
        )
        
        # LOGGING DE ÉXITO
        logger.info(
            "AUTENTICACIÓN EXITOSA - Usuario: %s, Expira: %s",
            credenciales.usuario,
            expiracion.isoformat()
        )
        
        # -----------------------------------------------------
        # FASE 4: RESPUESTA FINAL
        # -----------------------------------------------------
        return {
            "estado": 200,
            "mensaje": "Autenticación exitosa.",
            "usuario": credenciales.usuario,
            "token": token_generado,
            "expiracion": expiracion.isoformat()
        }
    
    except HTTPException:
        raise
    
    except Exception as excepcion_general:
        logger.error(
            "ERROR en autenticación - Usuario: %s",
            credenciales.usuario,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "estado": 500,
                "mensaje": "Error interno durante la autenticación.",
                "detalle": str(excepcion_general)
            }
        )
