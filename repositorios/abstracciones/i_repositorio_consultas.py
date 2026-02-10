"""
i_repositorio_consultas.py — Interface genérica para ejecutar consultas SQL parametrizadas
Ubicación: repositorios/abstracciones/i_repositorio_consultas.py

Equivalente a: ApiGenericaCsharp/Repositorios/Abstracciones/IRepositorioConsultas.cs

Arquitectura limpia: Solo métodos genéricos con dict[str, Any]
"""

from typing import Protocol, Any


class IRepositorioConsultas(Protocol):
    """
    Contrato genérico para repositorios que ejecutan consultas SQL parametrizadas.
    
    Arquitectura genérica:
    - Todos los métodos usan dict[str, Any] como parámetros
    - Completamente independiente del motor de base de datos
    - Tipos Python reales (datetime, int, bool) en lugar de strings
    """
    
    async def ejecutar_consulta_parametrizada_con_dictionary(
        self,
        consulta_sql: str,
        parametros: dict[str, Any],
        maximo_registros: int = 10000,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta consulta SQL parametrizada con Dictionary.
        
        Args:
            consulta_sql: Consulta SQL parametrizada (SELECT, WITH).
            parametros: Parámetros como diccionario con objetos Python tipados.
            maximo_registros: Límite máximo de registros.
            esquema: Esquema de BD opcional.
        
        Returns:
            Lista de diccionarios con resultados de la consulta.
        """
        ...
    
    async def validar_consulta_con_dictionary(
        self,
        consulta_sql: str,
        parametros: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Valida consulta SQL con Dictionary sin ejecutarla.
        """
        ...
    
    async def ejecutar_procedimiento_almacenado_con_dictionary(
        self,
        nombre_sp: str,
        parametros: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Ejecuta procedimiento almacenado con Dictionary.
        """
        ...
    
    async def obtener_esquema_tabla(
        self,
        nombre_tabla: str,
        esquema_predeterminado: str | None = None
    ) -> str | None:
        """
        Obtiene el esquema real donde existe una tabla específica.
        """
        ...
    
    async def obtener_estructura_tabla(
        self,
        nombre_tabla: str,
        esquema: str
    ) -> list[dict[str, Any]]:
        """
        Obtiene la estructura detallada de una tabla.
        """
        ...
    
    async def obtener_estructura_completa_base_datos(self) -> dict[str, Any]:
        """
        Obtiene la estructura completa de la base de datos.
        """
        ...
