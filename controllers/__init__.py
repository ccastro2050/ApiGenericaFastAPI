"""Controladores HTTP de la API."""
from .entidades_controller import router as entidades_controller
from .diagnostico_controller import router as diagnostico_controller
from .autenticacion_controller import router as autenticacion_controller
from .consultas_controller import router as consultas_controller
from .estructuras_controller import router as estructuras_controller

__all__ = [
    "entidades_controller",
    "diagnostico_controller",
    "autenticacion_controller",
    "consultas_controller",
    "estructuras_controller"
]
