"""
politica_tablas_prohibidas.py — Implementación que lee tablas prohibidas desde .env
Ubicación: servicios/politicas/politica_tablas_prohibidas.py

Equivalente a: ApiGenericaCsharp/Servicios/Politicas/PoliticaTablasProhibidasDesdeJson.cs

En Python/FastAPI leemos de variables de entorno (.env) en lugar de appsettings.json.
"""

from config import get_settings


class PoliticaTablasProhibidas:
    """
    Implementación que lee la lista de tablas prohibidas desde .env.
    
    Configuración esperada en .env:
        TABLAS_PROHIBIDAS=usuarios_sistema,configuracion_interna,auditoria
    
    Estrategia de validación:
    - Si la lista está vacía: TODAS las tablas están permitidas
    - Si la lista contiene tablas: Solo se PROHÍBEN las listadas
    - Comparación case-insensitive
    """
    
    def __init__(self):
        """
        Constructor que lee la configuración y prepara el set de tablas prohibidas.
        """
        settings = get_settings()
        
        # Leer tablas prohibidas de la configuración
        tablas_str = settings.security.tablas_prohibidas
        
        # Convertir a set con comparación case-insensitive
        if tablas_str:
            self._tablas_prohibidas: set[str] = {
                t.strip().lower() 
                for t in tablas_str.split(',') 
                if t.strip()
            }
        else:
            self._tablas_prohibidas = set()
    
    def es_tabla_permitida(self, nombre_tabla: str) -> bool:
        """
        Determina si una tabla está permitida verificando si NO está en la lista prohibida.
        
        Args:
            nombre_tabla: Nombre de la tabla a validar
        
        Returns:
            True si está permitida, False si está prohibida
        """
        # Nombres vacíos no están permitidos
        if not nombre_tabla or not nombre_tabla.strip():
            return False
        
        # Retorna True si NO está en la lista prohibida
        return nombre_tabla.lower().strip() not in self._tablas_prohibidas
    
    def obtener_tablas_prohibidas(self) -> frozenset[str]:
        """Método auxiliar para obtener la lista de tablas prohibidas (útil para debugging)."""
        return frozenset(self._tablas_prohibidas)
    
    def tiene_restricciones(self) -> bool:
        """Indica si hay restricciones configuradas."""
        return len(self._tablas_prohibidas) > 0
