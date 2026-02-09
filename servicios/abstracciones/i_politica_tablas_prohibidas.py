"""
i_politica_tablas_prohibidas.py — Protocol para validación de tablas permitidas/prohibidas
Ubicación: servicios/abstracciones/i_politica_tablas_prohibidas.py

Equivalente a: ApiGenericaCsharp/Servicios/Abstracciones/IPoliticaTablasProhibidas.cs

Principios SOLID aplicados:
- SRP: Responsabilidad única = decidir si una tabla está permitida
- DIP: Los servicios dependen de esta abstracción
- ISP: Protocol pequeño y específico con un solo método
"""

from typing import Protocol


class IPoliticaTablasProhibidas(Protocol):
    """
    Protocol que define el contrato para validar si una tabla está permitida.
    
    Propósito:
    - ServicioCrud no depende directamente de la configuración
    - Facilita testing con mocks
    - Permite cambiar la fuente de reglas sin modificar ServicioCrud
    """
    
    def es_tabla_permitida(self, nombre_tabla: str) -> bool:
        """
        Determina si una tabla está permitida para operaciones CRUD.
        
        Args:
            nombre_tabla: Nombre de la tabla a validar (case-insensitive)
        
        Returns:
            True si la tabla está permitida, False si está prohibida
        """
        ...
