"""
config.py — Configuración de la aplicación usando pydantic-settings
Ubicación: config.py (raíz del proyecto)

Lee variables de entorno desde .env y las expone como objetos tipados.
Equivalente en .NET: appsettings.json + IConfiguration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class ConfiguracionBaseDatos(BaseSettings):
    """Configuración de conexiones a bases de datos."""
    
    provider: str = Field(default="postgres")
    postgres: str = Field(default="postgresql+asyncpg://postgres:password@localhost:5432/mi_bd")
    sqlserver: str = Field(default="mssql+aioodbc://sa:password@localhost/mi_bd?driver=ODBC+Driver+17+for+SQL+Server")
    mysql: str = Field(default="mysql+aiomysql://root:password@localhost:3306/mi_bd")
    mariadb: str = Field(default="mysql+aiomysql://root:password@localhost:3306/mi_bd")

    class Config:
        env_prefix = "DB_"


class Settings(BaseSettings):
    """Configuración principal de la aplicación."""
    
    app_name: str = Field(default="ApiGenericaFastAPI")
    debug: bool = Field(default=True)
    database: ConfiguracionBaseDatos = Field(default_factory=ConfiguracionBaseDatos)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Obtiene la configuración (singleton con caché)."""
    return Settings()
