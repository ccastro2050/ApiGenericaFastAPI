"""Controladores HTTP de la API."""
from .entidades_controller import router as entidades_controller
from .diagnostico_controller import router as diagnostico_controller

__all__ = ["entidades_controller", "diagnostico_controller"]
