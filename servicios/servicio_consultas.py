"""
servicio_consultas.py — Implementación de lógica de negocio para consultas SQL parametrizadas
Ubicación: servicios/servicio_consultas.py

Equivalente a: ApiGenericaCsharp/Servicios/ServicioConsultas.cs

Arquitectura:
JSON → dict[str, Any] → IRepositorioConsultas → Motor específico
"""

import re
from typing import Any
from datetime import datetime

from config import get_settings
from repositorios.abstracciones.i_repositorio_consultas import IRepositorioConsultas
from servicios.utilidades.encriptacion_bcrypt import encriptar


class ServicioConsultas:
    """
    Implementación del servicio de consultas SQL parametrizadas.
    """
    
    def __init__(self, repositorio_consultas: IRepositorioConsultas):
        if repositorio_consultas is None:
            raise ValueError(
                "repositorio_consultas no puede ser None. "
                "Verificar configuración de dependencias."
            )
        self._repositorio = repositorio_consultas
        self._settings = get_settings()
    
    def validar_consulta_sql(
        self,
        consulta: str,
        tablas_prohibidas: list[str]
    ) -> tuple[bool, str | None]:
        """
        Valida que una consulta SQL sea segura para ejecutar.
        """
        if not consulta or not consulta.strip():
            return (False, "La consulta no puede estar vacía.")
        
        consulta_normalizada = consulta.strip().upper()
        
        # Solo permitir SELECT y WITH
        if not consulta_normalizada.startswith("SELECT") and not consulta_normalizada.startswith("WITH"):
            return (False, "Solo se permiten consultas SELECT y WITH por motivos de seguridad.")
        
        # Verificar tablas prohibidas
        for tabla in tablas_prohibidas:
            if tabla.lower() in consulta.lower():
                return (False, f"La consulta intenta acceder a la tabla prohibida '{tabla}'.")
        
        return (True, None)
    
    def _convertir_parametros_desde_json(
        self,
        parametros: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Convierte parámetros JSON a diccionario tipado.
        """
        parametros_genericos: dict[str, Any] = {}
        
        if parametros is None:
            return parametros_genericos
        
        for key, value in parametros.items():
            # Normalizar nombre del parámetro
            nombre = key if key.startswith("@") else f"@{key}"
            
            # Validar nombre
            if not re.match(r'^@\w+$', nombre):
                raise ValueError(f"Nombre de parámetro inválido: {nombre}")
            
            # Detectar tipo
            valor_tipado = self._detectar_tipo(value)
            parametros_genericos[nombre] = valor_tipado
        
        return parametros_genericos
    
    def _detectar_tipo(self, valor: Any) -> Any:
        """
        Detecta y convierte el tipo del valor.
        """
        if valor is None:
            return None
        
        if isinstance(valor, (int, float, bool, datetime)):
            return valor
        
        if isinstance(valor, str):
            return self._detectar_tipo_desde_string(valor)
        
        return valor
    
    def _detectar_tipo_desde_string(self, valor: str) -> Any:
        """
        Intenta detectar el tipo real desde un string.
        """
        if not valor:
            return valor
        
        # Intentar como datetime
        try:
            return datetime.fromisoformat(valor.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Intentar como int
        try:
            return int(valor)
        except ValueError:
            pass
        
        # Intentar como float
        try:
            return float(valor)
        except ValueError:
            pass
        
        # Intentar como bool
        if valor.lower() in ('true', 'false'):
            return valor.lower() == 'true'
        
        return valor
    
    async def ejecutar_consulta_parametrizada(
        self,
        consulta: str,
        parametros: dict[str, Any],
        maximo_registros: int = 10000,
        esquema: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta una consulta SQL parametrizada.
        """
        # Obtener tablas prohibidas
        tablas_prohibidas_str = self._settings.security.tablas_prohibidas
        tablas_prohibidas = [t.strip() for t in tablas_prohibidas_str.split(',') if t.strip()]
        
        # Validar consulta
        es_valida, mensaje_error = self.validar_consulta_sql(consulta, tablas_prohibidas)
        if not es_valida:
            raise PermissionError(mensaje_error or "Consulta no autorizada.")
        
        return await self._repositorio.ejecutar_consulta_parametrizada_con_dictionary(
            consulta, parametros, maximo_registros, esquema
        )
    
    async def ejecutar_consulta_parametrizada_desde_json(
        self,
        consulta: str,
        parametros: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta consulta con parámetros en formato JSON.
        """
        parametros_genericos = self._convertir_parametros_desde_json(parametros)
        return await self.ejecutar_consulta_parametrizada(
            consulta, parametros_genericos, 10000, None
        )
    
    async def ejecutar_procedimiento_almacenado(
        self,
        nombre_sp: str,
        parametros: dict[str, Any] | None,
        campos_a_encriptar: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Ejecuta un procedimiento almacenado.
        """
        if not nombre_sp or not nombre_sp.strip():
            raise ValueError("El nombre del procedimiento almacenado no puede estar vacío.")
        
        parametros_genericos = self._convertir_parametros_con_encriptacion(
            parametros, campos_a_encriptar
        )
        
        return await self._repositorio.ejecutar_procedimiento_almacenado_con_dictionary(
            nombre_sp, parametros_genericos
        )
    
    def _convertir_parametros_con_encriptacion(
        self,
        parametros: dict[str, Any] | None,
        campos_a_encriptar: list[str] | None
    ) -> dict[str, Any]:
        """
        Convierte parámetros y encripta los campos especificados.
        """
        parametros_genericos = self._convertir_parametros_desde_json(parametros)
        
        if campos_a_encriptar:
            for campo in campos_a_encriptar:
                clave = campo if campo.startswith("@") else f"@{campo}"
                
                if clave in parametros_genericos:
                    valor = parametros_genericos[clave]
                    if valor and isinstance(valor, str) and not valor.startswith("$2"):
                        parametros_genericos[clave] = encriptar(valor)
        
        return parametros_genericos
