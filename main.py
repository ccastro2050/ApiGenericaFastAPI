"""
Punto de entrada de la aplicación.
Equivalente a Program.cs en .NET
"""

from fastapi import FastAPI
from controllers import entidades_controller, diagnostico_controller, autenticacion_controller

# Crear la aplicación FastAPI
app = FastAPI(
    title="ApiGenericaFastAPI",
    description="API REST Genérica compatible con múltiples bases de datos",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc"
)

# Registrar los controladores (equivalente a app.MapControllers())
app.include_router(entidades_controller)
app.include_router(diagnostico_controller)
app.include_router(autenticacion_controller)


@app.get("/", tags=["Diagnóstico"])
async def root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {
        "mensaje": "ApiGenericaFastAPI está funcionando",
        "version": "1.0.0",
        "documentacion": "/swagger"
    }
