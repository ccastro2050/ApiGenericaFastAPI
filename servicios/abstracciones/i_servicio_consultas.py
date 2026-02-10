"""
i_servicio_consultas.py — Interface que define el contrato para ejecutar consultas SQL parametrizadas
Ubicación: servicios/abstracciones/i_servicio_consultas.py

Equivalente a: ApiGenericaCsharp/Servicios/Abstracciones/IServicioConsultas.cs

Principios SOLID aplicados:
- SRP: Esta interface solo define operaciones de consultas SQL parametrizadas
- DIP: Permite que el controlador dependa de esta abstracción
- ISP: Interface específica y pequeña
- OCP: Abierta para extensión, cerrada para modificación
"""

from typing import Protocol, Any


class IServicioConsultas(Protocol):
    """
    Contrato que define cómo ejecutar consultas SQL parametrizadas de forma segura.
    
    Esta interface es el "qué" (contrato), no el "cómo" (implementación).
    
    Diferencias con IServicioCrud:
    - IServicioCrud: Operaciones sobre tablas completas (SELECT * FROM tabla)
    - IServicioConsultas: Consultas SQL arbitrarias con parámetros personalizados
    """
    
    def validar_consulta_sql(
        self,
        consulta: str,
        tablas_prohibidas: list[str]
    ) -> tuple[bool, str | None]:
        """
        Valida que una consulta SQL sea segura para ejecutar.
        
        Args:
            consulta: Consulta SQL a validar. Debe ser SELECT válida.
            tablas_prohibidas: Lista de tablas que no pueden ser consultadas.
        
        Returns:
            Tupla (es_valida, mensaje_error):
            - (True, None) si la consulta es válida
            - (False, "mensaje") si hay error
        """
        ...
    
    async def ejecutar_consulta_parametrizada(
        self,
        consulta: str,
        parametros: dict[str, Any],
        maximo_registros: int = 10000,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta una consulta SQL parametrizada de forma segura.
        
        Args:
            consulta: Consulta SQL parametrizada.
            parametros: Diccionario de parámetros.
            maximo_registros: Límite máximo de registros.
            esquema: Esquema de BD opcional.
        
        Returns:
            Lista de diccionarios con los resultados.
        
        Raises:
            ValueError: Parámetros inválidos.
            PermissionError: Violación de políticas de seguridad.
            RuntimeError: Errores en la ejecución.
        """
        ...
    
    async def ejecutar_consulta_parametrizada_desde_json(
        self,
        consulta: str,
        parametros: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta consulta con parámetros en formato JSON.
        Método de conveniencia para controladores web.
        """
        ...
    
    async def ejecutar_procedimiento_almacenado(
        self,
        nombre_sp: str,
        parametros: dict[str, Any] | None,
        campos_a_encriptar: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta un procedimiento almacenado.
        
        Args:
            nombre_sp: Nombre del procedimiento almacenado.
            parametros: Diccionario de parámetros.
            campos_a_encriptar: Campos a encriptar con BCrypt.
        
        Returns:
            Lista de diccionarios con los resultados.
        """
        ...
