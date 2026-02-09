"""
Punto de entrada de la aplicación.
Equivalente a Program.cs en .NET
"""

from fastapi import FastAPI

# Crear la aplicación FastAPI
app = FastAPI(
    title="ApiGenericaFastAPI",
    description="API REST Genérica compatible con múltiples bases de datos",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc"
)


@app.get("/", tags=["Diagnóstico"])
async def root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {
        "mensaje": "ApiGenericaFastAPI está funcionando",
        "version": "1.0.0",
        "documentacion": "/swagger"
    }


@app.get("/weatherforecast", tags=["Demo"])
async def weather_forecast():
    """Endpoint de demostración (equivalente al template de .NET)."""
    import random
    from datetime import date, timedelta

    summaries = ["Freezing", "Bracing", "Chilly", "Cool", "Mild",
                 "Warm", "Balmy", "Hot", "Sweltering", "Scorching"]

    forecasts = []
    for i in range(5):
        forecasts.append({
            "date": str(date.today() + timedelta(days=i+1)),
            "temperatureC": random.randint(-20, 55),
            "summary": random.choice(summaries)
        })

    return forecasts
