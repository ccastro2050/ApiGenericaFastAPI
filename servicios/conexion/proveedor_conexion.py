"""
proveedor_conexion.py — Implementación que lee configuración desde .env
Ubicación: servicios/conexion/proveedor_conexion.py

Equivalente en .NET: ProveedorConexion.cs
"""

from config import Settings, get_settings


class ProveedorConexion:
    """
    Implementación que lee DB_PROVIDER y las cadenas de conexión desde .env.
    
    Equivalente en .NET: class ProveedorConexion : IProveedorConexion
    """

    def __init__(self, settings: Settings | None = None):
        """
        Constructor que recibe la configuración.
        
        El parámetro 'settings | None = None' significa:
        - settings puede ser de tipo Settings O puede ser None
        - Si no se pasa nada, el valor por defecto es None
        """
        self._settings = settings or get_settings()

    @property
    def proveedor_actual(self) -> str:
        """Lee el valor de DB_PROVIDER desde .env."""
        return self._settings.database.provider.lower().strip()

    def obtener_cadena_conexion(self) -> str:
        """Entrega la cadena de conexión correspondiente al proveedor actual."""
        provider = self.proveedor_actual
        db_config = self._settings.database

        # Diccionario que mapea proveedor → cadena de conexión
        cadenas = {
            "postgres": db_config.postgres,
            "postgresql": db_config.postgres,
            "sqlserver": db_config.sqlserver,
            "sqlserverexpress": db_config.sqlserverexpress,
            "localdb": db_config.localdb,
            "mysql": db_config.mysql,
            "mariadb": db_config.mariadb,
        }

        if provider not in cadenas:
            raise ValueError(
                f"Proveedor '{provider}' no soportado. "
                f"Opciones: {list(cadenas.keys())}"
            )

        cadena = cadenas[provider]
        
        if not cadena:
            raise ValueError(
                f"No se encontró cadena de conexión para '{provider}'. "
                f"Verificar DB_{provider.upper()} en .env"
            )

        return cadena
