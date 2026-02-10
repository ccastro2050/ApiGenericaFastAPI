"""Abstracciones de repositorios."""
from .i_repositorio_lectura_tabla import IRepositorioLecturaTabla
from .i_repositorio_consultas import IRepositorioConsultas

__all__ = ["IRepositorioLecturaTabla", "IRepositorioConsultas"]
