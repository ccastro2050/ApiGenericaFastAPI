"""
config.py — Configuración centralizada usando pydantic-settings
Ubicación: config.py

Equivalente a: ApiGenericaCsharp/appsettings.json + appsettings.Development.json

Jerarquía de configuración:
1. Se carga .env (configuración base/producción)
2. Se detecta ENVIRONMENT (development, production)
3. Se carga .env.{entorno} si existe (sobrescribe valores del base)

Variables de entorno:
- ENVIRONMENT=development  → Carga .env.development
- ENVIRONMENT=production   → Solo usa .env
- ENVIRONMENT=(no definida) → Solo usa .env
"""

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ================================================================
# DETECTAR ENTORNO
# ================================================================
def get_environment() -> str:
    """
    Detecta el entorno actual.
    Equivalente a ASPNETCORE_ENVIRONMENT en .NET
    """
    return os.getenv("ENVIRONMENT", "production").lower()


def get_env_file() -> str | tuple[str, str]:
    """
    Retorna el archivo .env a cargar según el entorno.

    En development: Carga .env primero, luego .env.development
    En production: Solo carga .env
    """
    env = get_environment()

    if env == "development":
        # Cargar .env base, luego .env.development sobrescribe
        env_dev = ".env.development"
        if os.path.exists(env_dev):
            return (".env", env_dev)

    return ".env"


# ================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ================================================================
class DatabaseSettings(BaseSettings):
    """
    Configuración de conexiones a base de datos.

    Equivalente a ConnectionStrings en appsettings.json
    """
    model_config = SettingsConfigDict(env_prefix='DB_')

    # Proveedor activo (equivalente a DatabaseProvider en C#)
    provider: str = Field(
        default='sqlserver',
        description="Proveedor activo: sqlserver, sqlserverexpress, localdb, postgres, mysql, mariadb"
    )

    # Cadenas de conexión por proveedor
    sqlserver: str = Field(
        default='',
        description="Cadena de conexión SQL Server"
    )
    sqlserverexpress: str = Field(
        default='',
        description="Cadena de conexión SQL Server Express"
    )
    localdb: str = Field(
        default='',
        description="Cadena de conexión SQL Server LocalDB (desarrollo)"
    )
    postgres: str = Field(
        default='',
        description="Cadena de conexión PostgreSQL"
    )
    mysql: str = Field(
        default='',
        description="Cadena de conexión MySQL"
    )
    mariadb: str = Field(
        default='',
        description="Cadena de conexión MariaDB"
    )


# ================================================================
# CONFIGURACIÓN DE JWT
# ================================================================
class JwtSettings(BaseSettings):
    """
    Configuración de autenticación JWT.

    Equivalente a sección Jwt en appsettings.json
    """
    model_config = SettingsConfigDict(env_prefix='JWT_')

    key: str = Field(
        default='MySuperSecretKey1234567890!@#$%^&*()_+',
        description="Clave secreta para firmar tokens (mínimo 32 caracteres)"
    )
    issuer: str = Field(
        default='MyApp',
        description="Quién emite el token (nombre de tu app)"
    )
    audience: str = Field(
        default='MyAppUsers',
        description="Para quién es el token (usuarios de tu app)"
    )
    duracion_minutos: int = Field(
        default=60,
        description="Tiempo de vida del token antes de expirar"
    )


# ================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ================================================================
class SecuritySettings(BaseSettings):
    """
    Configuración de seguridad.

    Equivalente a TablasProhibidas en appsettings.json
    """
    tablas_prohibidas: str = Field(
        default='',
        alias='TABLAS_PROHIBIDAS',
        description="Tablas que la API no puede acceder, separadas por coma"
    )


# ================================================================
# CONFIGURACIÓN PRINCIPAL
# ================================================================
class Settings(BaseSettings):
    """
    Configuración principal de la aplicación.

    Equivalente a la combinación de appsettings.json + appsettings.Development.json
    """
    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Modo debug (equivalente a Logging en C#)
    debug: bool = Field(
        default=False,
        alias='DEBUG',
        description="Activa modo debug con logs detallados"
    )

    # Entorno actual
    environment: str = Field(
        default_factory=get_environment,
        description="Entorno: development, production"
    )

    # Sub-configuraciones
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


# ================================================================
# SINGLETON DE CONFIGURACIÓN
# ================================================================
@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración (singleton cacheado).

    El decorador @lru_cache asegura que solo se crea una instancia.
    """
    return Settings()


# ================================================================
# NOTAS PEDAGÓGICAS
# ================================================================
#
# 1. EQUIVALENCIAS CON C#:
#    - appsettings.json         → .env
#    - appsettings.Development  → .env.development
#    - ASPNETCORE_ENVIRONMENT   → ENVIRONMENT
#    - IConfiguration           → get_settings()
#
# 2. JERARQUÍA:
#    Production:  Solo .env
#    Development: .env + .env.development (sobrescribe)
#
# 3. PREFIJOS DE VARIABLES:
#    - DB_*   → DatabaseSettings
#    - JWT_*  → JwtSettings
#    - Otros  → Settings directamente
