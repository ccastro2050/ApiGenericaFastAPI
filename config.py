"""
config.py — Configuración centralizada usando pydantic-settings
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Configuración de base de datos."""
    model_config = SettingsConfigDict(env_prefix='DB_')
    
    provider: str = Field(default='sqlserver')
    sqlserver: str = Field(default='')
    postgres: str = Field(default='')
    mysql: str = Field(default='')
    mariadb: str = Field(default='')


class JwtSettings(BaseSettings):
    """Configuración de JWT."""
    model_config = SettingsConfigDict(env_prefix='JWT_')
    
    key: str = Field(default='MySuperSecretKey1234567890')
    issuer: str = Field(default='MyApp')
    audience: str = Field(default='MyAppUsers')
    duracion_minutos: int = Field(default=60)


class SecuritySettings(BaseSettings):
    """Configuración de seguridad."""
    
    tablas_prohibidas: str = Field(default='', alias='TABLAS_PROHIBIDAS')


class Settings(BaseSettings):
    """Configuración principal de la aplicación."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )
    
    debug: bool = Field(default=False, alias='DEBUG')
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)


@lru_cache()
def get_settings() -> Settings:
    """Obtiene la configuración (singleton cacheado)."""
    return Settings()
