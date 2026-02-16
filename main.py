"""
main.py — Punto de entrada de la API Genérica
Ubicación: main.py

Equivalente a: ApiGenericaCsharp/Program.cs

Configuración de:
- Aplicación FastAPI (equivalente a WebApplication.CreateBuilder)
- CORS (Cross-Origin Resource Sharing)
- Middleware de autenticación
- Documentación Swagger/OpenAPI
- Registro de controladores (routers)

Arquitectura:
    main.py
        │
        ├── 1. Importar dependencias
        ├── 2. Cargar configuración
        ├── 3. Crear aplicación FastAPI (Swagger incluido)
        ├── 4. Configurar CORS
        ├── 5. Registrar controladores (routers)
        └── 6. Endpoint raíz de diagnóstico
"""

# ================================================================
# IMPORTS
# ================================================================

# FastAPI y middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configuración
from config import get_settings

# Controladores (equivalente a app.MapControllers() en C#)
from controllers import (
    entidades_controller,
    diagnostico_controller,
    autenticacion_controller,
    consultas_controller,
    estructuras_controller,
    procedimientos_controller
)


# ================================================================
# CARGAR CONFIGURACIÓN
# ================================================================

# Obtiene la configuración desde .env / .env.development
# Equivalente a: builder.Configuration en C#
settings = get_settings()


# ================================================================
# REGISTRO DE DEPENDENCIAS
# ================================================================
#
# Equivalente al switch en Program.cs (C#) líneas 154-194.
# La fábrica centraliza la selección de proveedor en UN solo lugar.
# Para agregar un nuevo proveedor, solo se modifica fabrica_repositorios.py.
#
# Ver: servicios/fabrica_repositorios.py

from servicios.fabrica_repositorios import (  # noqa: E402
    crear_repositorio_lectura,
    crear_repositorio_consultas,
    crear_servicio_crud,
    crear_servicio_consultas,
)


# ================================================================
# CREAR APLICACIÓN FASTAPI
# ================================================================

# Equivalente a:
#   var builder = WebApplication.CreateBuilder(args);
#   var app = builder.Build();
#
# FastAPI incluye Swagger automáticamente (no necesita AddSwaggerGen)

app = FastAPI(
    # Metadatos de la API (se muestran en Swagger)
    title="API Genérica CRUD Multi-Base de Datos",
    description="""
API REST genérica para operaciones CRUD sobre cualquier tabla.

**Características:**
- Soporta SQL Server, PostgreSQL, MySQL/MariaDB
- Autenticación JWT
- Consultas SQL parametrizadas
- Ejecución de procedimientos almacenados
- Introspección de estructura de BD

**Documentación alternativa:** [ReDoc](/redoc)
    """,
    version="1.0.0",

    # Rutas de documentación
    # Equivalente a: app.UseSwagger() y app.UseSwaggerUI()
    docs_url="/swagger",      # Swagger UI en /swagger
    redoc_url="/redoc",       # ReDoc en /redoc
    openapi_url="/swagger/v1/swagger.json",  # Esquema OpenAPI

    # Información de contacto (opcional)
    contact={
        "name": "API Genérica",
        "url": "https://github.com/tu-usuario/ApiGenericaFastAPI",
    },

    # Licencia (opcional)
    license_info={
        "name": "MIT",
    },
)


# ================================================================
# CONFIGURACIÓN DE CORS
# ================================================================

# Equivalente a:
#   builder.Services.AddCors(opts => {
#       opts.AddPolicy("PermitirTodo", politica => politica
#           .AllowAnyOrigin()
#           .AllowAnyMethod()
#           .AllowAnyHeader()
#       );
#   });
#   app.UseCors("PermitirTodo");
#
# ¿Por qué CORS?
# Sin esto, un frontend en localhost:3000 no puede llamar a una API en localhost:8000
# El navegador bloquea la petición por seguridad (Same-Origin Policy)

app.add_middleware(
    CORSMiddleware,
    # Orígenes permitidos (dominios que pueden consumir la API)
    # "*" = cualquier origen (equivalente a AllowAnyOrigin)
    allow_origins=["*"],

    # Permite cookies y headers de autenticación
    allow_credentials=True,

    # Métodos HTTP permitidos (equivalente a AllowAnyMethod)
    allow_methods=["*"],

    # Headers permitidos (equivalente a AllowAnyHeader)
    allow_headers=["*"],
)


# ================================================================
# REGISTRO DE CONTROLADORES (ROUTERS)
# ================================================================

# Equivalente a: app.MapControllers() en C#
#
# En FastAPI, cada controlador es un "Router" que se registra con include_router()
# La inyección de dependencias (DI) se hace en cada endpoint con Depends()
#
# Diferencia con C#:
# - C#: builder.Services.AddScoped<IServicio, Servicio>() (registro global)
# - Python: Depends(obtener_servicio) (registro por endpoint)

# IMPORTANTE: Orden de registro importa. Los routers más específicos van primero.
app.include_router(diagnostico_controller)    # Health checks
app.include_router(autenticacion_controller)  # Login/JWT
app.include_router(consultas_controller)      # Consultas SQL
app.include_router(estructuras_controller)    # Introspección BD
app.include_router(procedimientos_controller) # Stored Procedures
app.include_router(entidades_controller)      # CRUD genérico (al final por tener prefix="/api" genérico)


# ================================================================
# ENDPOINT RAÍZ (DIAGNÓSTICO)
# ================================================================

@app.get("/", tags=["Diagnóstico"])
async def root():
    """
    Endpoint raíz para verificar que la API está funcionando.

    Equivalente a un health check básico.

    Returns:
        dict: Estado de la API con versión y enlaces útiles
    """
    return {
        "mensaje": "ApiGenericaFastAPI está funcionando",
        "version": "1.0.0",
        "entorno": settings.environment,
        "documentacion": {
            "swagger": "/swagger",
            "redoc": "/redoc",
            "openapi": "/swagger/v1/swagger.json"
        }
    }


# ================================================================
# EVENTO DE INICIO (OPCIONAL)
# ================================================================

@app.on_event("startup")
async def startup_event():
    """
    Se ejecuta cuando la aplicación inicia.

    Equivalente a código después de app.Build() en C#.
    Útil para:
    - Verificar conexión a BD
    - Cargar cachés
    - Inicializar servicios
    """
    import logging
    logging.info(
        "API iniciada en modo: %s | Proveedor BD: %s",
        settings.environment,
        settings.database.provider
    )


# ================================================================
# EJECUCIÓN DIRECTA (DESARROLLO)
# ================================================================

# Permite ejecutar con: python main.py
# En producción usar: uvicorn main:app --host 0.0.0.0 --port 8000

if __name__ == "__main__":
    import uvicorn

    # Configuración de uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,  # Auto-reload en desarrollo
        log_level="debug" if settings.debug else "info"
    )


# ================================================================
# NOTAS PEDAGÓGICAS
# ================================================================
#
# 1. EQUIVALENCIAS CON C#:
#
#    | C# (.NET)                          | Python (FastAPI)                |
#    |------------------------------------|--------------------------------|
#    | WebApplication.CreateBuilder()     | FastAPI()                      |
#    | builder.Services.AddControllers()  | (automático)                   |
#    | builder.Services.AddCors()         | app.add_middleware(CORS...)    |
#    | builder.Services.AddSwaggerGen()   | (automático con FastAPI)       |
#    | builder.Services.AddScoped<>()     | Depends() en cada endpoint     |
#    | app.UseAuthentication()            | Middleware personalizado       |
#    | app.UseCors()                      | add_middleware(CORSMiddleware) |
#    | app.MapControllers()               | app.include_router()           |
#    | app.Run()                          | uvicorn.run()                  |
#
# 2. INYECCIÓN DE DEPENDENCIAS:
#
#    C# (registro global):
#        builder.Services.AddScoped<IServicioCrud, ServicioCrud>();
#
#    Python (por endpoint):
#        @router.get("/")
#        async def endpoint(servicio: ServicioCrud = Depends(obtener_servicio)):
#            ...
#
# 3. ORDEN DE MIDDLEWARE:
#    En FastAPI el orden de add_middleware es INVERSO al de ejecución.
#    El último middleware agregado se ejecuta primero.
#
# 4. DOCUMENTACIÓN AUTOMÁTICA:
#    FastAPI genera Swagger automáticamente desde los type hints.
#    No necesita configuración adicional como en C#.
